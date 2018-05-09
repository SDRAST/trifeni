import logging
import Pyro4

from .util import SSHTunnelManager, check_connection
from .errors import TunnelError

__all__ = ["Pyro4Tunnel", "DaemonTunnel", "NameServerTunnel"]

module_logger = logging.getLogger(__name__)

class Pyro4Tunnel(SSHTunnelManager):
    """
    Base class for interacting with remote Pyro4 objects.

    Attributes:
        remote_server_name (str): name of remote server, or alias to remote server
            (as defined in configuration)
        relay_ip (str): the address through which the tunnel is routed. If we
            were creating the tunnel using the command line ssh, this would correspond
            to the address given to the -L option
        remote_port (int): port on which to login to remote server (-p option in
            command line ssh client)
        remote_username (str): username to login in remote server. (-l option in
            command line ssh client)
        local (bool): Boolean indicating whether to create a tunnel or not.
        create_tunnel_kwargs (dict): dictionary options passed to the super class's
            ``create_tunnel`` method.
    """
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

    def register_remote_daemon(self, daemon, reverse=True):
        """
        Register a remote daemon with the remote Pyro4 nameserver.
        This creates a tunnel to the daemon object. Note that in "local" mode there
        is no reason to do this.

        Args:
            daemon (Pyro4.Daemon):
        Returns:
            bool: Whether or not the connection was already there.
        """
        if not self.local:
            daemon_host, daemon_port = daemon.locationStr.split(":")
            self.create_tunnel(int(daemon_port), int(daemon_port), reverse=reverse, **self.create_tunnel_kwargs)

    def create_tunnel(self, local_port, remote_port, reverse=False):
        """Overridden create tunnel method"""
        return super(Pyro4Tunnel, self).create_tunnel(
            self.remote_server_name, self.relay_ip, local_port, remote_port,
            port=self.remote_port, username=self.remote_username,reverse=reverse,**self.create_tunnel_kwargs)

class DaemonTunnel(Pyro4Tunnel):
    """
    Find a daemon on the remote without a nameserver connection.

    Examples:

    .. code-block:: python

        uri = "PYRO:Server@localhost:9091"
        with DaemonTunnel(remote_server_name="remote_alias") as dt:
            proxy = dt.get_remote_object(uri)

    """
    def get_remote_object(self, uri, remote_port=None, proxy_class=None):
        """
        Given some Pyro URI, create connection to a Daemon sitting on a remote server.

        Examples:

        Assuming we have some DaemonTunnel object already instantiated:

        .. code-block:: python

            >>> uri = "PYRO:Server@localhost:9091"
            >>> proxy = dt.get_remote_object(uri)
            >>> proxy.square(2)
            4

        Args:
            uri (str/Pyro4.core.URI): URI of remote object.
            remote_port (port, optional): The remote daemon might be sitting on a
                different port than the ``uri`` would have us believe.
            proxy_class (object, optional): Proxy class. Defaults to Pyro4.Proxy
        Returns:
            object: instance of a Proxy class.
        """
        if proxy_class is None:
            proxy_class = Pyro4.Proxy

        if not self.local:
            uri = Pyro4.core.URI(uri)
            obj_host, obj_port = uri.location.split(":")
            if remote_port is None:
                remote_port = obj_port
            self.create_tunnel(int(obj_port), int(remote_port))
            proxy = proxy_class(uri)
            if hasattr(proxy, "_daemon"): # we need to create reverse tunnel to daemon
                d_host, d_port = proxy._daemon.locationStr.split(":")
                self.create_tunnel(int(d_port), int(d_port), reverse=True)
            if not check_connection(proxy._pyroBind):
                raise TunnelError(
                    ("Failed to create tunneled connection to object with uri {}, "
                     "forwarding port {} to {}").format(uri, obj_port, remote_port)
                )
        elif self.local:
            proxy = proxy_class(uri)
        return proxy

class NameServerTunnel(Pyro4Tunnel):
    """
    Create a tunnel to the remote nameserver.

    Examples:

    .. code-block:: python

        with NameServerTunnel(remote_server_name="remote_alias",ns_port=9090) as ns:
            obj_proxy = ns.get_remote_object("SomeCoolObject")
            obj_proxy.some_cool_method()

    Attributes:
        ns_host (str): remote Pyro4 nameserver host
        ns_port (int): remote Pyro4 nameserver port
        ns (Pyro4.naming.NameServer): Pyro4 nameserver instance
    """
    def __init__(self, ns_host="localhost",
                       ns_port=9090,
                       local_ns_port=None,
                       **kwargs):

        super(NameServerTunnel, self).__init__(**kwargs)
        self.ns_host = ns_host
        self.ns_port = int(ns_port)
        self.ns = self.find_nameserver(local_ns_port=local_ns_port)

    def __getattr__(self, attr):
        """
        Act like we're interacting with a Pyro4 nameserver proxy.
        """
        if self.ns is not None:
            return getattr(self.ns, attr)
        else:
            raise TunnelError("Coulnd't find nameserver attribute")

    def find_nameserver(self,local_ns_port=None):
        """
        Find the remote nameserver. This gets called by __init__.

        Examples:

        If I have a nameserver running locally on port 9090, and there is a
        nameserver on the remote running on 9090, I can't forward port 9090 to the
        remote! Enter the ``local_ns_port`` keyword argument:

        .. code-block:: python

            tunnel = NameServerTunnel(remote_server_name="remote_alias", ns_port=9090)
            ns = tunnel.find_nameserver(local_ns_port=9091)

        Args:
            local_ns_port (int, optional): Use a local forwarding port that is different
                from self.ns_port.
        Returns:
            Pyro4.naming.NameServer
        """
        self.logger.info(
            "Attempting to find remote nameserver. Remote IP: {}, NS port: {}".format(
                self.remote_server_name, self.ns_port
            )
        )
        if local_ns_port is None:
            local_ns_port = self.ns_port

        if not self.local:
            self.create_tunnel(local_ns_port, self.ns_port,**self.create_tunnel_kwargs)
            # now we check the connection to see if its running.
            if check_connection(Pyro4.locateNS, args=(self.ns_host, local_ns_port)):
                return Pyro4.locateNS(self.ns_host, local_ns_port)
            else:
                # Would be cool to add ip address and stuff to error message.
                exc = TunnelError("Failed to find NameServer on tunnel.")
                exc.details = {'remote_server_name':self.remote_server_name}
                raise exc
        else:
            return Pyro4.locateNS(self.ns_host, local_ns_port)

    def get_remote_object(self, remote_obj_name, local_obj_port=None, proxy_class=None):
        """
        Grab an object registered on the remote nameserver.

        Args:
            remote_obj_name (str): The name of the Pyro object registered on the
                nameserver.
        Returns:
            Pyro4.core.URI: URI corresponding to requested pyro object, or
                None if connections wasn't successful.
        """
        if proxy_class is None: proxy_class = Pyro4.core.Proxy
        obj_uri = self.ns.lookup(remote_obj_name)
        if self.local:
            return proxy_class(obj_uri)
        else:
            obj_host, obj_port = obj_uri.location.split(":")
            if not local_obj_port:
                local_obj_port = int(obj_port)
            self.create_tunnel(local_obj_port, int(obj_port), **self.create_tunnel_kwargs)
            return proxy_class(obj_uri)

    def cleanup(self):
        if self.ns is not None:
            self.ns._pyroRelease()
        super(NameServerTunnel, self).cleanup()

if __name__ == '__main__':
    pass
