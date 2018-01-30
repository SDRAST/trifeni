import unittest

from pyro4tunneling.pyro4tunnel import Tunnel, NameServerTunnel, DaemonTunnel
from . import create_tunnel_test

class TestTunnel(create_tunnel_test()):

    def test_create_tunnel(self):
        tunnel = Tunnel(remote_server_name="me")
        proc, existing = tunnel.create_tunnel(9091, 9090)

    def test_clean_up(self):
        pass

@unittest.skip("")
class TestNameServerTunnnel(create_tunnel_test()):

    pass

@unittest.skip("")
class TestDaemonTunnel(create_tunnel_test()):

    pass

if __name__ == "__main__":
    unittest.main()
