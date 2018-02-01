import uuid
import re
import time
import threading
import logging
import sys
import getpass
import os
import socket
import select
try:
    import SocketServer
except ImportError:
    import socketserver as SocketServer

import paramiko

from ..configuration import config

__all__ = [
    "SSHTunnel",
    "SSHTunnelManager"
]

module_logger = logging.getLogger(__name__)

class ForwardServer(SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

class ForwardHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        try:
            chan = self.ssh_transport.open_channel("direct-tcpip",
                                                   (self.chain_host, self.chain_port),
                                                   self.request.getpeername())
        except Exception as e:
            module_logger.debug("Handler.handler: Incoming request to {}:{} failed: {}".format(
                self.chain_host,self.chain_port, err
            ))
            return
        if chan is None:
            module_logger.debug(
                "Handler.handler: Incoming request to {}:{} was rejected by the SSH server.".format(
                    self.chain_host, self.chain_port
            ))
            return

        module_logger.debug("Handler.handler: Connected!  Tunnel open {} -> {} -> {}:{}".format(
                    self.request.getpeername(),chan.getpeername(),self.chain_host, self.chain_port
        ))
        while True:
            # I think this is where we relay data between client and server
            r, w, x = select.select([self.request, chan], [], [])
            if self.request in r:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                self.request.send(data)

        peername = self.request.getpeername()
        chan.close()
        self.request.close()
        module_logger.debug("Handler.handler: Tunnel closed from {}".format(peername))

def reverse_handler(chan, host, port):
    sock = socket.socket()
    try:
        sock.connect((host, port))
    except Exception as e:
        module_logger.debug("handler: Forwarding request to {}:{} failed: {}".format(host, port, e))
        return

    module_logger.debug("handler: Connected!  Tunnel open {} -> {} -> {}".format(chan.origin_addr,
                                                        chan.getpeername(), (host, port)))
    while True:
        r, w, x = select.select([sock, chan], [], [])
        if sock in r:
            data = sock.recv(1024)
            if len(data) == 0:
                break
            chan.send(data)
        if chan in r:
            data = chan.recv(1024)
            if len(data) == 0:
                break
            sock.send(data)
    chan.close()
    sock.close()
    module_logger.debug("Tunnel closed from {}".format(chan.origin_addr,))

class SSHTunnel(object):

    __slots__ = ("remote_ip","relay_ip","local_port","remote_port",
                "port","username","tunnel_id","thread","client","open")

    def __init__(self, remote_ip=None, relay_ip=None,
                    local_port=None, remote_port=None,
                    port=None, username=None, tunnel_id=None,
                    tunnel_thread=None, client=None):

        self.remote_ip = remote_ip
        self.relay_ip = relay_ip
        self.local_port = local_port
        self.port = port
        self.username = username
        self.tunnel_id = tunnel_id
        self.thread = tunnel_thread
        self.client = client
        self.open = True

    def destroy(self):
        if self.client is not None:
            self.client.close()
        self.open = False
        # if self.thread is not None:
        #     self.thread.join()

class SSHTunnelManager(object):

    def __init__(self, logger=None):
        self.tunnels = {}
        if logger is None: logger = logging.getLogger(
            module_logger.name + self.__class__.__name__
        )
        self.logger = logger

    def create_tunnel(self,
                    remote_ip, relay_ip,
                    local_port, remote_port,
                    port=22, username=None,
                    keyfile=None,look_for_keys=False,
                    wait_for_password=False,reverse=False,
                    tunnel_id=None):

        if remote_ip in config.hosts:
            remote_alias = remote_ip
            remote_info = config.hosts[remote_alias]
            port = remote_info["Port"]
            username = remote_info["User"]
            remote_ip = remote_info["HostName"]
            keyfile = remote_info.get("IdentityFile", None)
            self.logger.debug("create_tunnel: remote_info for host alias {}: {}".format(remote_alias, remote_info))

        if tunnel_id is None:
            tunnel_id = uuid.uuid4().hex

        if username is None:
            username = getpass.getuser()

        if keyfile is None:
            keyfile = config.default_identity_file
        else:
            look_for_keys = False

        if not os.path.exists(keyfile):
            self.logger.error("create_tunnel: Couldn't find keyfile {}".format(keyfile))
        else:
            self.logger.debug("create_tunnel: Using private keyfile {}".format(keyfile))

        password = None
        if wait_for_password:
            password = getpass.getpass("create_tunnel: Enter SSH password: ")

        self.logger.debug(
            "create_tunnel: creating tunnel to remote host {}:{}. Forwarding port {} to {} using relay_ip {}".format(
                remote_ip, port, local_port, remote_port, relay_ip
            )
        )
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())

        try:
            client.connect(remote_ip, port, username=username, key_filename=keyfile,
                           look_for_keys=look_for_keys, password=password)

        except Exception as err:
            self.logger.error("create_tunnel: Failed to connect to {}:{}: {}".format(remote_ip,port, err))
            return

        transport = client.get_transport()

        def forward_tunnel():
            class SubHander(ForwardHandler):
                chain_host = relay_ip
                chain_port = remote_port
                ssh_transport = transport
            ForwardServer(("", local_port), SubHander).serve_forever()

        def reverse_tunnel():
            transport.request_port_forward("", local_port)
            while True:
                print("here")
                chan = transport.accept(1000)
                if chan is None:
                    continue
                reverse_thread = threading.Thread(target=reverse_handler, args=(chan, relay_ip, remote_port))
                reverse_thread.daemon = True
                reverse_thread.start()

        if reverse:
            tunnel_thread = threading.Thread(target=reverse_tunnel)
        else:
            tunnel_thread = threading.Thread(target=forward_tunnel)
        tunnel_thread.daemon = True
        tunnel_thread.start()
        tunnel = SSHTunnel(remote_ip=remote_ip,
                        relay_ip=relay_ip,local_port=local_port,
                        remote_port=remote_port,port=port,username=username,
                        tunnel_id=tunnel_id,tunnel_thread=tunnel_thread,
                        client=client)
        self.tunnels[tunnel_id] = tunnel
        return tunnel
