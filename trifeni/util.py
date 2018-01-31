# util.py
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
import shlex
import subprocess
try:
    import SocketServer
except ImportError:
    import socketserver as SocketServer

import paramiko

from .configuration import config, config_logger

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


class Process(object):
    """
    Class representing a basic process, with name and pid.
    A Process object is used to represent an already running process.
    To spawn a new process, use subprocess.subprocess.Popen.
    Public Attributes:
        name (str): The name of the process
        pid (int): The process ID
    Public Members:
        kill: kill the process
    """

    def __init__(self, name="", pid=0, ps_line=None, command_name='ssh'):
        """
        Create Process instance.
        Keyword Args:
            name (str): The name of the process
            pid (int): the process id
        """

        self.name = name
        try:
            self.pid = int(pid)
        except ValueError:
            module_logger.error("Provided PID is not valid. Won't be able to call kill")
        if ps_line:
            self.name, self.pid = self.process_ps_line(ps_line, command_name)

    def process_ps_line(self, ps_line, command_name):
        """
        Given a line from the output of `ps x`, get the name and pid of the process.
        Returns:

        """
        re_pid = re.compile("\d+")
        re_name = re.compile("{}.*".format(command_name))
        id = int(re_pid.findall(ps_line)[0])
        name = re_name.findall(ps_line)[0]
        return name, id

    def kill(self):

        os.kill(self.pid, signal.SIGKILL)


def invoke_cmd(command, command_input=None):
    """
    Create a subprocess.Popen instance corresponding to a bash command.
    Args:
        command (str): The command to be invoked
    """
    args = shlex.split(command)

    module_logger.debug("invoke: argument list is %s", str(args))

    proc = subprocess.Popen(args, shell=False,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    # proc = subprocess.Popen(args, shell=False,
    #                         stdout=subprocess.PIPE,
    #                         stderr=subprocess.PIPE,
    #                         stdin=subprocess.PIPE)

    proc.stdin.write(command_input)
    proc.stdin.flush()
    stdout, stderr = proc.communicate()
    print(stdout, stderr)
    # waiting = True
    # while waiting:
    #     try:
    #         proc.stdin.write(command_input)
    #         print("here")
    #         output = proc.stdout.readlines()
    #         print("here")
    #         # if command_input is not None:
    #         #     proc.stdin.write(command_input)
    #         #     proc.stdin.flush()
    #         waiting = False
    #     except IOError:
    #         continue

    return proc


def pipe_cmds(command1, command2):
    """
    Pipe to commands together. Useful for things like `ps x | grep python`
    Args:
        command1 (str): The initial command to run
        command2 (str): The command to receive stdout of command1
    Returns:
        list: Output of piped command
    """
    p1 = subprocess.Popen(shlex.split(command1), stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split(command2), stdin=p1.stdout, stdout=subprocess.PIPE)
    waiting = True
    while waiting:
        try:
            output = p2.stdout.readlines()
            waiting = False
        except IOError:
            continue
    return output

def kill_processes(search_term, match_template=None):
    """
    Kill processes that contain match_template
    Args:
        search_term (str): The process to look for (python, ssh)
    Keyword Arguments:
        match_template (str): A string that processes should contain in order to
            be killed.
    """
    processes = pipe_cmds("ps x","grep {}".format(search_term))
    for proc in processes:
        if match_template in proc:
            bp = Process(ps_line=proc, command_name=search_term)
            bp.kill()

def check_connection(callback, timeout=1.0, attempts=10, args=None, kwargs=None):
    """
    Check to see if a connection is viable, by running a callback.
    Args:
        callback: The callback to test the connection
    Keyword Args:
        timeout (float): The amount of time to wait before trying again
        attempts (int): The number of times to try to connect.
        args: To be passed to callback
        kwargs: To be passed to callback

    Returns:
        bool: True if the connection was successful, False if not successful.
    """
    if not kwargs: kwargs = {}
    if not args: args = ()
    attempt_i = 0
    while attempt_i < attempts:
        try:
            callback(*args, **kwargs)
            module_logger.debug("Successfully connected.")
            return True
        except Exception as e:
            module_logger.debug("Connection failed: {}. Timing out".format(e))
            time.sleep(timeout)
            attempt_i += 1
    module_logger.error("Connection failed completely.")
    return False


def arbitrary_tunnel(remote_ip, relay_ip,
                     local_port, remote_port,
                     port=22, username='',reverse=False, password=None):
    """
    Create an arbitrary ssh tunnel, after checking to see if a tunnel already exists.
    This just spawns the process that creates the tunnel, it doesn't check to see if the tunnel
    has successfully connected.

    Executes the following command (if reverse is False, otherwise the -L is replaced with -R):
    ```
    ssh  -p {port} -l {username} -L {local_port}:{relay_ip}:{remote_port} {remote_ip}
    ```
    Args:
        remote_ip (str): The remote, or target ip address.
            For local port forwarding this can be localhost
        relay_ip (str): The relay ip address.
        local_port (int): The local port on which we listen
        remote_port (int): The remote port on which we listen
    Keyword Args:
        port (int): The -p argument for ssh
        username (str): The username to use for tunneling
    Returns:
        subprocess.Popen: if there isn't an existing process corresponding to tunnel:
            or else Process instance, the corresponds to already running tunnel command.

    """
    module_logger.debug("Configuration: {}".format(config.hosts))
    # Regular or reverse tunnel?
    if reverse:
        tag = "-R"
    else:
        tag = "-L"

    command = None

    if remote_ip in config.hosts:
        if config.hosts[remote_ip] == list():
            command_template = "ssh -N {0} {1}:{2}:{3} {4}"
            command = command_template.format(tag, local_port, relay_ip, remote_port, remote_ip)
        else:
            remote_ip, username, port = config.hosts[remote_ip]

    if not command:
        command_template = "ssh -N -l {0} -p {1} {2} {3}:{4}:{5} {6}"
        command = command_template.format(username, port,
                                tag, local_port, relay_ip,
                                remote_port, remote_ip)

    command_relay = "{0} {1}:{2}:{3} {4}".format(tag, local_port, relay_ip, remote_port, remote_ip)
    ssh_proc = [str(proc) for proc in pipe_cmds('ps x', 'grep ssh')]
    for proc in ssh_proc:
        if command_relay in proc:
            bp = Process(ps_line=proc, command_name='ssh')
            module_logger.debug("Found matching process: {}, pid: {}".format(bp.name,bp.pid))
            return (bp, True)
    module_logger.debug("Invoking command {}".format(command))
    p = invoke_cmd(command,command_input=password)
    return (p, False)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("paramiko").setLevel(logging.ERROR)
    tm = TunnelManager()
    # t = tm.create_tunnel("riselka", "localhost", 50001, 50001)
    tm.create_tunnel("localhost","localhost",9091, 9090, wait_for_password=True, username="dean",port=4674)
    while True:
        pass
