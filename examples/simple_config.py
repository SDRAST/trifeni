import logging

import pyro4tunneling
from pyro4tunneling.pyro4tunnel import Pyro4Tunnel

logging.basicConfig(level=logging.DEBUG)

t = Pyro4Tunnel('do-droplet',ns_port=50000)
bs = t.get_remote_object("BasicServer")
print(type(bs))
print(bs.square(2))
