# nameserver_tunnel_example
"""
Examples showing how one might use the nameserver tunnel.

Here we assume that a nameserver is running on the remote server on port 9090,
and that it has an object "SomeCoolObject" registered on it.

Much of the syntax for interacting with the NameServerTunnel is the same as
the DaemonTunnel. See examples/daemon_tunnel_example.py
"""
import Pyro4

import trifeni

# like with the DaemonTunnel, its useful to use context managers
with trifeni.NameServerTunnel(remote_server_name="remote_alias",ns_port=9090) as ns:
    obj_proxy = ns.get_remote_object("SomeCoolObject")
    obj_proxy.some_cool_method()
