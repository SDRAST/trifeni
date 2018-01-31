import unittest

import Pyro4

from trifeni.pyro4tunnel import NameServerTunnel, DaemonTunnel
from . import create_tunnel_test

class TestNameServerTunnnel(create_tunnel_test()):
    pass

class TestDaemonTunnel(create_tunnel_test()):

    def test_init(self):
        pass

    # @unittest.skip("")
    def test_get_remote_object(self):
        uri = "PYRO:TestServer@localhost:50001"
        dt = DaemonTunnel(remote_server_name="me")
        p = dt.get_remote_object(uri, remote_port=50000)
        self.assertTrue(p.square(2) == 4)

    def test_get_remote_object_local(self):
        uri = "PYRO:TestServer@localhost:50000"
        dt = DaemonTunnel(remote_server_name="me",local=True)
        p = dt.get_remote_object(uri)
        self.assertTrue(p.square(2) == 4)

if __name__ == "__main__":
    unittest.main()
