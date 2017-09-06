import unittest
import logging
import os

from pyro4tunneling import config

test_dir = os.path.dirname(os.path.abspath(__file__))

class TestConfig(unittest.TestCase):

    def test_default_ssh_config(self):
        config.ssh_default_configure()

    def test_ssh_config_file(self):
        config.ssh_configure(os.path.join(test_dir, "pyro4tunneling.json"))
        self.assertTrue("remote" in config.hosts)
        config.hosts = {}

    def test_ssh_config_dict(self):
        config.ssh_configure({'host': ["hostname", "myname", 22]})
        self.assertTrue("host" in config.hosts)
        config.hosts = {}

if __name__ == "__main__":
    logging.basicConfig(loglevel=logging.DEBUG)

    unittest.main()
