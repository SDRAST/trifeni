import unittest

import Pyro4

from trifeni.pyro4tunnel import NameServerTunnel, DaemonTunnel
from . import create_tunnel_test

@unittest.skip("")
class TestNameServerTunnnel(create_tunnel_test()):

    def setUp(self):
        self.ns_tunnel = NameServerTunnel(ns_port=9090, local_ns_port=9091)
        self.ns_tunnel_local = NameServerTunnel(ns_port=9090, local=True)

    def tearDown(self):
        pass

    def test_list_daemons(self):
        daemons = self.ns_tunnel.list()
        self.assertTrue(isinstance(daemons, list))

    def test_list_daemons_local(self):
        daemons = self.ns_tunnel_local.list()
        self.assertTrue(isinstance(daemons, list))

    def test_get_remote_object(self):
        test_server_proxy = self.ns_tunnel.get_remote_object("TestServer")

    def test_get_remote_object_local(self):
        test_server_proxy = self.ns_tunnel_local.get_remote_object("TestServer")

class TestDaemonTunnel(create_tunnel_test()):

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
