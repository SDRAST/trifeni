import unittest
import threading
try:
    import SocketServer
except ImportError:
    import socketserver as SocketServer # python3

class Server(SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

class Handler(SocketServer.BaseRequestHandler):

    def handle(self):
        self.data = self.request.recv(1024).strip()
        print(self.data)

def create_tunnel_test():

    class BaseTest(unittest.TestCase):

        @classmethod
        def setUpClass(cls):
            host, port = "localhost", 9090
            server = Server((host,port),Handler)
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()

    return BaseTest
