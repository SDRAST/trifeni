import logging
import Pyro4

from .util import arbitrary_tunnel, check_connection
from .autoreconnectingproxy import AutoReconnectingProxy

__all__ = ["TunnelError", "Tunnel", "DaemonTunnel", "NameServerTunnel"]

module_logger = logging.getLogger(__name__)

class TunnelError(Pyro4.errors.CommunicationError):
    pass

class Tunnel(object):
    """
    A generic tunneling class. This allows for creation and maintenance of
    arbitrary tunnels.
    """
    def __init__(self,  remote_server_name='localhost',
                        relay_ip='localhost',
                        remote_port=22,
                        remote_username="",
                        logger=None):
        if not logger:
            self.logger = logging.getLogger(module_logger.name + self.__class__.__name__)
        else:
            self.logger = logger
        self.remote_server_name = remote_server_name
        self.relay_ip = relay_ip
        self.remote_port = remote_port
        self.remote_username = remote_username
        self.processes = []

    def create_tunnel(self, forwarding_port, target_port, reverse=False):
        proc, existing = arbitrary_tunnel(
            self.remote_server_name, self.relay_ip, forwarding_port, target_port,
            port=self.remote_port, username=self.remote_username, reverse=reverse
        )
        self.processes.append(proc)
        return proc, existing

    def cleanup(self):
        """
        Remove any existing SSH connections.
        """
        for proc in self.processes:
            try:
                self.logger.debug("Attempting to kill process {}".format(proc))
                proc.kill()
                self.logger.debug("Successfully killed process {}".format(proc))
            except Exception as err:
                self.logger.error("""Couldn't kill process {} due to {}.
                                    If you don't want this connection to persist, you'll have to kill manually""".format(
                                        proc, err
                                    ))

class DaemonTunnel(Tunnel):
    """
    A tunnel that doesn't bother with finding nameservers.
    """
    def create_daemon_tunnel(self, daemon, reverse=True):
        host, port = daemon.locationStr.split(":")
        if not self.local:
            proc, existing = self.create_tunnel(port, port)
        else:
            existing = True
        return existing

class NameServerTunnel(Tunnel):
    """
    Create a tunnel to the remote nameserver
    """
    def __init__(self,
                ns_host="localhost",
                ns_port=9090,
                local_forwarding_port=None,
                local=False, **kwargs):

        super(NameServerTunnel, self).__init__(**kwargs)
        self.ns_host = ns_host
        self.ns_port = ns_port
        self.local_forwarding_port = local_forwarding_port
        self.local = local
        if not self.local_forwarding_port:
            self.local_forwarding_port = self.ns_port
        self.processes = []
        self.ns = self.find_nameserver()

    def find_nameserver(self):
        """
        Find the remote nameserver.
        Returns:
            Pyro4.naming.NameServer
        """
        self.logger.info(
            "Attempting to find remote nameserver. Remote IP: {}, NS port: {}".format(
                self.remote_server_name, self.ns_port
            )
        )
        # First we create ssh tunnel to remote ip.
        if not self.local:
            proc, existing = self.create_tunnel(self.local_forwarding_port, self.ns_port)
            # proc, existing = arbitrary_tunnel(self.remote_server_name, self.relay_ip, self.local_forwarding_port, self.ns_port,
            #                  port=self.remote_port, username=self.remote_username)
            # self.processes.append(proc)
            # now we check the connection to see if its running.
            if check_connection(Pyro4.locateNS, args=(self.ns_host, self.ns_port)):
                return Pyro4.locateNS(self.ns_host, self.ns_port)
            else:
                # Would be cool to add ip address and stuff to error message.
                exc = TunnelError("Failed to find NameServer on tunnel.")
                exc.details = {'remote_server_name':self.remote_server_name}
                raise exc
        else:
            return Pyro4.locateNS(self.ns_host, self.ns_port)

    def register_remote_daemon(self, daemon, reverse=True):
        """
        Register a remote daemon with the NameServerObject. This creates a
        tunnel to the daemon object. Note that in "local" mode there
        is no reason to
        Args:
            daemon (Pyro4.Daemon):
        Returns:
            bool: Whether or not the connection was already there.
        """
        if self.local:
            return True
        else:
            daemon_host, daemon_port = daemon.locationStr.split(":")
            proc, existing = self.create_tunnel(daemon_port, daemon_port, reverse=reverse)
            # proc_daemon, existing = arbitrary_tunnel(self.remote_server_name, self.relay_ip, daemon_port,
            #                                daemon_port, username=self.remote_username,
            #                                port=self.remote_port, reverse=reverse)
            # self.processes.append(proc_daemon)
            return existing

    def get_remote_object(self, remote_obj_name, remote_obj_port=None, remote_obj_id=None, auto=False):
        """
        Grab an object registered on the remote nameserver.
        Args:
            remote_obj_name (str): The name of the Pyro object.
        Returns:
            Pyro4.URI corresponding to requested pyro object, or
            None if connections wasn't successful.
        """
        obj_uri = self.ns.lookup(remote_obj_name)
        if self.local:
            if auto:
                return AutoReconnectingProxy(obj_uri)
            else:
                return Pyro4.Proxy(obj_uri)
        else:
            obj_proxy = Pyro4.Proxy(obj_uri)
            obj_host, obj_port = obj_uri.location.split(":")
            proc, existing = arbitrary_tunnel(self.remote_server_name, self.relay_ip, obj_port,
                                        obj_port, username=self.remote_username, port=self.remote_port)

            self.processes.append(proc)
            if check_connection(obj_proxy._pyroBind):
                if auto:
                    obj_proxy = AutoReconnectingProxy(obj_uri)
                else:
                    obj_proxy = Pyro4.Proxy(obj_uri)
                return obj_proxy
            else:
                exc = TunnelError("Failed to find remote object on remote nameserver.")
                exc.details = {'remote_server_name':self.remote_server_name}
                raise exc

    def cleanup(self):
        """
        Remove any existing SSH connections.
        """
        for proc in self.processes:
            try:
                self.logger.debug("Attempting to kill process {}".format(proc))
                proc.kill()
                self.logger.debug("Successfully killed process {}".format(proc))
            except Exception as err:
                self.logger.error("""Couldn't kill process {} due to {}.
                                    If you don't want this connection to persist, you'll have to kill manually""".format(
                                        proc, err
                                    ))


if __name__ == '__main__':
    pass
