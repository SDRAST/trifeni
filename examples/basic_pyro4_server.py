import argparse

import Pyro4

class BasicServer(object):

    @Pyro4.expose
    def square(self, x):
        return x**2

    @Pyro4.expose
    @Pyro4.oneway
    def square_with_callback(self, x, callback_info):
        res = x**2
        callback = getattr(callback_info["handler"], callback_info["callback_name"])
        callback(res)

def parse_args(init_description):
    parser = argparse.ArgumentParser(description=init_description)

    parser.add_argument("--ns_host", "-nsn", dest='ns_host', action='store', default='localhost', type=str,
                        help="Specify a host name for the Pyro name server. Default is \"localhost\".")

    parser.add_argument("--ns_port", "-nsp", dest='ns_port', action='store', default=9090, type=int,
                        help="Specify a port number for the Pyro name server. Default is 9090.")

    parser.add_argument("--obj_port", "-op", dest='obj_port', action='store', default=0, type=int,
                        help="Specify a port on which to register daemon. Default is 0 (random).")

    return parser


if __name__ == '__main__':
    parsed = parse_args("Start a basic server").parse_args()
    bs = BasicServer()
    print("Attempting to register server on name server")
    with Pyro4.Daemon(host='localhost', port=parsed.obj_port) as daemon:
        server_uri = daemon.register(bs, objectId=bs.__class__.__name__)
        print("Daemon URI is {}".format(server_uri))
        try:
            with Pyro4.locateNS(port=parsed.ns_port, host=parsed.ns_host) as ns:
                ns.register('BasicServer', server_uri)
        except Pyro4.errors.NamingError as err:
            print("Couldn't find specified nameserver, not registering daemon on nameserver.")
        daemon.requestLoop()
