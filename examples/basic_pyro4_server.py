import argparse

import Pyro4


class BasicServer(object):
    def __init__(self):
        pass

    @Pyro4.expose
    def square(self, x):
        """
        Square argument
        args:
            x (int/float): The argument to be square.
        returns:
            float: The result of the arguemnt squared
        """
        return x ** 2


def parse_args(init_description):
    """
    Grab arguments relevant to the Pyro nameserver that have APC and Spectrometer servers 
    registered. 
    """
    parser = argparse.ArgumentParser(description=init_description)

    parser.add_argument("--ns_host", "-nsn", dest='ns_host', action='store', default='localhost',
                        help="Specify a host name for the Pyro name server. Default is localhost")

    parser.add_argument("--ns_port", "-nsp", dest='ns_port', action='store', default=9090, type=int,
                        help="Specify a port number for the Pyro name server. Default is 9090.")

    return parser.parse_args()


if __name__ == '__main__':
    parsed = parse_args("Start a basic server")
    bs = BasicServer()
    print("Registering basic server on name server")
    print("Server registered at {}:{}".format(parsed.ns_host, parsed.ns_port))
    with Pyro4.Daemon(host='localhost', port=50001) as daemon:
        server_uri = daemon.register(bs, objectId='BasicServer')
        with Pyro4.locateNS(port=parsed.ns_port, host=parsed.ns_host) as ns:
            ns.register('BasicServer', server_uri)
        daemon.requestLoop()
