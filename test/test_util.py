import logging
import time
import unittest
import sys

from trifeni import util, config

module_logger = logging.getLogger(__name__)

class TestUtil(unittest.TestCase):

    def test_init_tunnel_manager(self):

        tm = util.SSHTunnelManager()

    def test_create_tunnel(self):
        
        tm = util.SSHTunnelManager()
        t = tm.create_tunnel("me","localhost",9091,9090,reverse=False)
        module_logger.debug("test_create_tunnel: tunnel {}".format(t))
        time.sleep(2.0)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("paramiko").setLevel(logging.ERROR)
    if "me" not in config.hosts:
        print("Need to configure a \"me\" ssh alias to use tunneling tests")
        sys.exit(1)
    unittest.main()
