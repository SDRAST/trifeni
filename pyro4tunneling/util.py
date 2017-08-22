import logging
import time
import re
import os
import signal
import shlex
import subprocess

from .configuration import config

module_logger = logging.getLogger(__name__)

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


def invoke_cmd(command):
    """
    Create a subprocess.Popen instance corresponding to a bash command.
    Args:
        command (str): The command to be invoked
    """
    args = shlex.split(command)

    module_logger.debug("invoke: argument list is %s", str(args))

    proc = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

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

def check_connection(callback, timeout=1.0, attempts=10, args=(), kwargs={}):
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
                     port=22, username='',reverse=False):
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
    p = invoke_cmd(command)
    return (p, False)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    # kill_processes('ssh', '-L')
