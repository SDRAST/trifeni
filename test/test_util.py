import unittest

from pyro4tunneling import util

class TestUtil(unittest.TestCase):

    def test_arbitrary_tunnel(self):
        util.arbitrary_tunnel("localhost","localhost",
                                9090, 4674, port=4674,username="dean",
                                password="hawkeye\n")

if __name__ == "__main__":
    unittest.main()
