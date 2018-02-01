import logging
import unittest
import threading

import Pyro4
import Pyro4.naming

from trifeni.util import check_connection

module_logger = logging.getLogger(__name__)

@Pyro4.expose
class TestServer(object):
    def square(self, x):
        return x**2
    def repeat(self, sequence, times,delimiter=" "):
        repeated = delimiter.join([sequence for i in range(int(times))])
        return repeated

def create_tunnel_test():

    class BaseTest(unittest.TestCase):

        @classmethod
        def setUpClass(cls):
            server, host, ns_port, obj_port = TestServer(), "localhost", 9090, 50000
            ns_uri, ns_daemon, ns_server = Pyro4.naming.startNS(port=ns_port)
            ns_thread = threading.Thread(target=ns_daemon.requestLoop)
            ns_thread.daemon = True
            ns_thread.start()

            with Pyro4.locateNS(port=ns_port) as ns:
                daemon = Pyro4.Daemon(port=obj_port)
                uri = daemon.register(server, objectId=server.__class__.__name__)
                ns.register(server.__class__.__name__, uri)
                daemon_thread = threading.Thread(target=daemon.requestLoop)
                daemon_thread.daemon = True
                daemon_thread.start()

            cls.server = server
            cls.host = host
            cls.ns_port = ns_port
            cls.obj_port = obj_port

            cls.ns_daemon = ns_daemon
            cls.obj_daemon = daemon

        @classmethod
        def tearDownClass(cls):
            cls.obj_daemon.shutdown()
            cls.ns_daemon.shutdown()

    return BaseTest
