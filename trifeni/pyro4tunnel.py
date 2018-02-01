import logging
import Pyro4

from .util import SSHTunnelManager

__all__ = ["TunnelError", "Pyro4Tunnel", "DaemonTunnel", "NameServerTunnel"]

module_logger = logging.getLogger(__name__)

class TunnelError(Pyro4.errors.CommunicationError):
    pass

class Pyro4Tunnel(SSHTunnelManager):

    def __init__(self,remote_server_name='localhost',
                       relay_ip='localhost',
                       remote_port=22,
                       remote_username=None,local=False,
                       create_tunnel_kwargs=None,logger=None):

        super(Pyro4Tunnel, self).__init__(logger=logger)
        self.remote_server_name = remote_server_name
        self.relay_ip = relay_ip
        self.remote_port = remote_port
        self.remote_username = remote_username
        self.local = local
        if not create_tunnel_kwargs: create_tunnel_kwargs = {}
        self.create_tunnel_kwargs = create_tunnel_kwargs

    def create_tunnel(self, local_port, remote_port, reverse=False):
        return super(Pyro4Tunnel, self).create_tunnel(
            self.remote_server_name, self.relay_ip, local_port, remote_port,
            port=self.remote_port, username=self.remote_username,reverse=reverse,**self.create_tunnel_kwargs)

class DaemonTunnel(Pyro4Tunnel):
    """
    Find a daemon on the remote without a nameserver connection.
    """
    def get_remote_object(self, uri, remote_port=None, proxy_class=None, reverse=False):
        """
        Given some Pyro URI, create connection to a Daemon sitting on a remote server.
        """
        if proxy_class is None:
            proxy_class = Pyro4.Proxy
        if not self.local:
            uri = Pyro4.core.URI(uri)
            obj_host, obj_port = uri.location.split(":")
            if remote_port is None:
                remote_port = obj_port
            self.create_tunnel(int(obj_port), int(remote_port), reverse=reverse)
        return proxy_class(uri)

class NameServerTunnel(Pyro4Tunnel):
    """
    Create a tunnel to the remote nameserver
    """
    def __init__(self, ns_host="localhost",
                       ns_port=9090,
                       **kwargs):

        super(NameServerTunnel, self).__init__(**kwargs)
        self.ns_host = ns_host
        self.ns_port = int(ns_port)
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
            self.create_tunnel(self.ns_port, self.ns_port,**self.create_tunnel_kwargs)
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

    def register_remote_daemon(self, daemon, reverse=True, **kwargs):
        """
        Register a remote daemon with the NameServerObject. This creates a
        tunnel to the daemon object. Note that in "local" mode there
        is no reason to
        Args:
            daemon (Pyro4.Daemon):
        Returns:
            bool: Whether or not the connection was already there.
        """
        if not self.local:
            daemon_host, daemon_port = daemon.locationStr.split(":")
            self.create_tunnel(daemon_port, daemon_port, reverse=reverse, **self.create_tunnel_kwargs)

    def get_remote_object(self, remote_obj_name, proxy_class=None):
        """
        Grab an object registered on the remote nameserver.
        Args:
            remote_obj_name (str): The name of the Pyro object.
        Returns:
            Pyro4.URI corresponding to requested pyro object, or
            None if connections wasn't successful.
        """
        if proxy_class is None: proxy_class = Pyro4.core.Proxy
        obj_uri = self.ns.lookup(remote_obj_name)
        if self.local:
            return proxy_class(obj_uri)
        else:
            obj_host, obj_port = obj_uri.location.split(":")
            self.create_tunnel(int(obj_port), int(obj_port), **self.create_tunnel_kwargs)
            return proxy_class(obj_uri)

if __name__ == '__main__':
    pass
