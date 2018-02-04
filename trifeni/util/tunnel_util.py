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

from .shell_util import check_connection
from ..configuration import config

__all__ = [
    "SSHTunnel",
    "SSHTunnelManager",
    "test_port"
]

module_logger = logging.getLogger(__name__)

class ForwardServer(SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)

class ForwardHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        try:
            chan = self.ssh_transport.open_channel("direct-tcpip",
                                                   (self.chain_host, self.chain_port),
                                                   self.request.getpeername())
        except Exception as err:
            module_logger.debug("ForwardHandler.handler: Incoming request to {}:{} failed: {}".format(
                self.chain_host,self.chain_port, err
            ))
            return
        if chan is None:
            module_logger.debug(
                "ForwardHandler.handler: Incoming request to {}:{} was rejected by the SSH server.".format(
                    self.chain_host, self.chain_port
            ))
            return

        module_logger.debug("ForwardHandler.handler: Connected!  Tunnel open {} -> {} -> {}:{}".format(
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
        module_logger.debug("ForwardHandler.handler: Tunnel closed from {}".format(peername))

class ReverseHandler(object):

    def __init__(self, transport, relay_ip, remote_port):

        self.running = threading.Event()
        self.running.set()
        self.transport = transport
        self.relay_ip = relay_ip
        self.remote_port = remote_port
        self.reverse_thread = None

    def reverse_handler(self, chan):
        sock = socket.socket()
        host, port = self.relay_ip, self.remote_port
        try:
            sock.connect((host, port))
        except Exception as err:
            module_logger.debug("handler: Forwarding request to {}:{} failed: {}".format(host, port, err))
            return

        module_logger.debug("handler: Connected!  Tunnel open {} -> {} -> {}".format(chan.origin_addr,
                                                            chan.getpeername(), (host, port)))
        while self.running.is_set():
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

    def serve_forever(self):
        module_logger.debug("ReverseHandler.serve_forever: called")
        while self.running.is_set():
            module_logger.debug("ReverseHandler.serve_forever: top of while loop")
            chan = self.transport.accept(1000)
            if chan is None:
                continue
            self.reverse_thread = threading.Thread(target=self.reverse_handler, args=(chan,))
            self.reverse_thread.daemon = True
            self.reverse_thread.start()
            module_logger.debug("ReverseHandler.shutdown: bottom of while loop")

    def shutdown(self):
        module_logger.debug("ReverseHandler.shutdown: called")
        self.running.clear()
        module_logger.debug("ReverseHandler.shutdown: self.running cleared")
        if self.reverse_thread is not None:
            self.reverse_thread.join()
        module_logger.debug("ReverseHandler.shutdown: finished")

    def server_close(self):
        pass


class SSHTunnel(object):
    """
    Create either forward or reverse SSH tunnels using paramiko and
    socket servers.

    Instance Attributes:
        remote_ip (str): host address of the server to which we are trying to
            connect
        relay_ip (str): host address of relay server
        local_port (int): The local forwarding port
        remote_port (int): The remote forwarding port
        port (int): The port associated with remote_ip, ie a port on which
            remote_ip is listening
        username (str): The username to use for connecting to remote_ip
        tunnel_id (str): A UUID for this tunnel
        tunnel_thread (threading.Thread): a thread on which the socket server
            runs
        client (paramiko.SSHClient): The paramiko SSH client
        server (server instance): socket server.
        reverse (bool): Whether or not this is a reverse tunnel
        open (bool): Whether or not the tunnel is active
        logger (logging.getLogger)
        keyfile (str): path to SSH key

    In terms of the ssh cli, some of these slots can be thought of as follows:

        ssh -l username -p port -L local_port:relay_ip:remote_port remote_ip

    """
    def __init__(self,
                remote_ip, relay_ip,
                local_port, remote_port,
                port=22, username=None,
                keyfile=None,look_for_keys=False,
                wait_for_password=False,reverse=False,
                tunnel_id=None, logger=None):
        """
        If argument/keyword argument descriptions aren't specified, see
        description of Instance Attributes.
        Args:
            remote_ip (str): This can either be an actual server address, or
                the name of a SSH alias defined in trifeni.config (these
                normally come from a SSH config file in "~/.ssh/config")
            relay_ip (str)
            local_port (int)
            remote_port (int)
        Keyword Args:
            port (int): (22)
            username (str): (None)
            keyfile (str): (None)
            look_for_keys (bool): Passed to self.connect (False)
            wait_for_password (bool):  Passed to self.connect (False)
            reverse (bool): (False)
            tunnel_id (str): (None)
            logger (logging.getLogger): (None)
        """
        if logger is None: logger = logging.getLogger(module_logger.name+".SSHTunnel")
        self.logger = logger

        if remote_ip in config.hosts:
            remote_alias = remote_ip
            remote_info = config.hosts[remote_alias]
            port = remote_info["Port"]
            username = remote_info.get("User", None)
            remote_ip = remote_info["HostName"]
            keyfile = remote_info.get("IdentityFile", None)
            self.logger.debug("__init__: remote_info for host alias {}: {}".format(remote_alias, remote_info))

        self.remote_ip = remote_ip
        self.port = port
        self.relay_ip = relay_ip
        self.local_port = local_port
        self.remote_port = remote_port
        self.reverse = reverse

        if username is None:
            username = getpass.getuser()
        self.username = username

        if keyfile is None:
            keyfile = config.default_identity_file
        else:
            look_for_keys = False
        self.keyfile = keyfile

        if not os.path.exists(self.keyfile):
            self.logger.error("__init__: Couldn't find keyfile {}".format(keyfile))
            look_for_keys = True
            wait_for_password = True
        else:
            self.logger.debug("__init__: Using private keyfile {}".format(keyfile))

        if tunnel_id is None:
            tunnel_id = uuid.uuid4().hex
        self.tunnel_id = tunnel_id
        self.tunnel_thread = None
        self.client = None
        self.server = None
        self.open = False

        if self.reverse:
            self.connect(look_for_keys=look_for_keys, wait_for_password=wait_for_password)
        else:
            if not self.check_conflict():
                self.connect(look_for_keys=look_for_keys, wait_for_password=wait_for_password)
            else:
                raise RuntimeError("Will not be able to bind {}:{}".format(self.relay_ip, self.local_port))

    def connect(self,look_for_keys=False, wait_for_password=False):
        """
        Establish the tunnel connection. This will not check to see if this tunnel
        will conflict with any existing tunnels, instead it will likely through
        an error when either trying to 1) bind the paramiko SSH client, or 2)
        bind the socket server.

        Keyword Arguments:
            look_for_keys (bool): Automatically look for SSH keys.
            wait_for_password (bool): If true, program execution will hang until
                user inputs password
        """
        password = None
        if wait_for_password:
            password = getpass.getpass("create_tunnel: Enter SSH password: ")

        self.logger.debug(
            "connect: creating tunnel to remote host {}:{}. Forwarding port {} to {} using relay_ip {}".format(
                self.remote_ip, self.port, self.local_port, self.remote_port, self.relay_ip
            )
        )
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())

        try:
            client.connect(self.remote_ip, self.port, username=self.username, key_filename=self.keyfile,
                           look_for_keys=look_for_keys, password=password)

        except Exception as err:
            self.logger.error("create_tunnel: Failed to connect to {}:{}: {}".format(self.remote_ip, self.port, err))
            return

        transport = client.get_transport()

        def forward_tunnel():
            class SubHander(ForwardHandler):
                chain_host = self.relay_ip
                chain_port = self.remote_port
                ssh_transport = transport
            def server_factory():
                return ForwardServer(("", self.local_port), SubHander)
            return server_factory()

        def reverse_tunnel():
            transport.request_port_forward("", self.local_port)
            server = ReverseHandler(transport, self.relay_ip, self.remote_port)
            return server

        if self.reverse:
            server = reverse_tunnel()
        else:
            server = forward_tunnel()

        tunnel_thread = threading.Thread(target=server.serve_forever)
        tunnel_thread.daemon = True
        tunnel_thread.start()

        self.client = client
        self.server = server
        self.tunnel_thread = tunnel_thread
        self.open = True

    def check_conflict(self):
        """
        Returns True if there is a conflict, False if there isn't one.
        """
        # if self.remote_ip == self.relay_ip:
        #     self.logger.debug(("Won't determine if there will be conflicts if "
        #                        "relay_ip and remote_ip are the same"))
            # return False
        # else:
        return test_port(self.local_port, host=self.relay_ip)

    def destroy(self):
        """Destroy the tunnel."""
        self.logger.debug("destroy: {} called".format(self.tunnel_id))
        if self.client is not None:
            self.logger.debug("destroy: calling self.client.close")
            self.client.close()
        if self.server is not None:
            self.logger.debug("destroy: calling self.server.shutdown")
            self.server.shutdown()
            self.server.server_close() # this is necessary to completely unbind the server.
        # module_logger.debug("destroy: joining tunnel thread")
        # module_logger.debug("destroy: self.tunnel_thread.daemon: {}".format(self.tunnel_thread.daemon))
        # self.tunnel_thread.join()
        # module_logger.debug("destroy: tunnel thread joined")
        self.open = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.destroy()

class SSHTunnelManager(object):
    """
    Create and manage SSH tunnel connections.
    """
    def __init__(self, logger=None):
        self.tunnels = {}
        if logger is None: logger = logging.getLogger(
            module_logger.name + self.__class__.__name__
        )
        self.logger = logger

    def create_tunnel(self, remote_ip, relay_ip, local_port, remote_port, **kwargs):
        """Create an instance of SSHTunnel and add it to the tunnels attribute
        and attempt to detect whether there will be collisions.
        """
        local_ports = [(self.tunnels[_id].relay_ip, self.tunnels[_id].local_port) for _id in self.tunnels]
        if (relay_ip, local_port) in local_ports:
            self.logger.debug(
                ("This tunnel manager is already responsible "
                 "for a tunnel bound to {}:{}").format(relay_ip, local_port))
            return

        tunnel = SSHTunnel(remote_ip, relay_ip, local_port, remote_port, **kwargs)
        self.tunnels[tunnel.tunnel_id] = tunnel
        return tunnel

    def destroy_tunnel(self, _id):
        """
        Destroy a tunnel by id
        Args:
            _id (str): The id of the tunnel to destroy
        """
        self.tunnels[_id].destroy()

    def cleanup(self):
        """
        Destroy all the tunnels associated with the manager. Note that this
        doesn't actually delete the SSHTunnel objects from memory.
        """
        self.logger.debug("cleanup: Killing {} tunnels".format(len(self.tunnels)))
        for tunnel_id in self.tunnels:
            self.logger.debug("cleanup: Destroying tunnel {}".format(tunnel_id))
            self.tunnels[tunnel_id].destroy()

    def tunnel_status(self):
        """
        Return a dict with tunnel ids as keys, and with each tunnel's
        open attribute
        """
        return {_id:self.tunnels[_id].open for _id in self.tunnels}

    def __str__(self):
        super_str = super(SSHTunnelManager, self).__str__()
        return "{} tunnel status: {}".format(super_str, self.tunnel_status())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

def test_port(port, host="localhost"):
    """
    Determine if a port is already being used. Returns False if not bound,
    True if bound.
    Args:
        port (int): The port to check
    Keyword Args:
        host (str): The host to attempt to bind on ("localhost")
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
        sock.close()
        # sock.shutdown(1)
        # sock.server_close()
    except socket.error as err:
        if err.errno == 98:
            module_logger.debug("test_port: {}".format(err))
            return True
        else:
            raise err

    return False
