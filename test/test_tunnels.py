import unittest
import logging

import Pyro4

from trifeni.pyro4tunnel import NameServerTunnel, DaemonTunnel
from . import create_tunnel_test

module_logger = logging.getLogger(__name__)

# @unittest.skip("")
class TestNameServerTunnnel(create_tunnel_test()):

    def setUp(self):
        self.ns_tunnel = NameServerTunnel(remote_server_name="me",
                                        ns_port=9090, local_ns_port=9091)

        self.ns_tunnel_local = NameServerTunnel(remote_server_name="me",
                                        ns_port=9090, local=True)

    def tearDown(self):
        self.ns_tunnel.cleanup()
        self.ns_tunnel_local.cleanup()

    def test_list_daemons(self):
        daemons = self.ns_tunnel.list()
        module_logger.debug("test_list_daemons: {}".format(daemons))
        self.assertTrue(isinstance(daemons, dict))
        self.assertTrue("TestServer" in daemons)

    @unittest.skip("")
    def test_list_daemons_local(self):
        daemons = self.ns_tunnel_local.list()
        module_logger.debug("test_list_daemons_local: {}".format(daemons))
        self.assertTrue(isinstance(daemons, dict))
        self.assertTrue("TestServer" in daemons)

    @unittest.skip("")
    def test_get_remote_object(self):
        test_server_proxy = self.ns_tunnel.get_remote_object("TestServer")

    @unittest.skip("")
    def test_get_remote_object_local(self):
        test_server_proxy = self.ns_tunnel_local.get_remote_object("TestServer")

@unittest.skip("")
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
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("paramiko").setLevel(logging.INFO)
    unittest.main()
