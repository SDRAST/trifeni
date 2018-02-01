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

    # @unittest.skip("")
    def test_list_daemons(self):
        daemons = self.ns_tunnel.list()
        module_logger.info("test_list_daemons: {}".format(daemons))
        self.assertTrue(isinstance(daemons, dict))
        self.assertTrue("TestServer" in daemons)

    # @unittest.skip("")
    def test_list_daemons_local(self):
        daemons = self.ns_tunnel_local.list()
        module_logger.info("test_list_daemons_local: {}".format(daemons))
        self.assertTrue(isinstance(daemons, dict))
        self.assertTrue("TestServer" in daemons)

    # @unittest.skip("")
    def test_get_remote_object(self):
        test_server_proxy = self.ns_tunnel.get_remote_object("TestServer",
                                                        local_obj_port=50001)
        module_logger.info("test_get_remote_object: got {} from get_remote_object".format(test_server_proxy))
        self.assertTrue(test_server_proxy.square(2) == 4)

    # @unittest.skip("")
    def test_get_remote_object_local(self):
        test_server_proxy = self.ns_tunnel_local.get_remote_object("TestServer")
        module_logger.info("test_get_remote_object_local: got {} from get_remote_object".format(test_server_proxy))
        self.assertTrue(test_server_proxy.square(2) == 4)

# @unittest.skip("")
class TestDaemonTunnel(create_tunnel_test()):

    def test_get_remote_object(self):
        uri = "PYRO:TestServer@localhost:50001"
        with DaemonTunnel(remote_server_name="me") as dt:
            p = dt.get_remote_object(uri, remote_port=50000)
            self.assertTrue(p.square(2) == 4)

    def test_get_remote_object_local(self):
        uri = "PYRO:TestServer@localhost:50000"
        with DaemonTunnel(remote_server_name="me",local=True) as dt:
            p = dt.get_remote_object(uri)
            self.assertTrue(p.square(2) == 4)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("paramiko").setLevel(logging.ERROR)
    unittest.main()
