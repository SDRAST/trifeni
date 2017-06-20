import logging

from pyro4tunneling import Pyro4Tunnel, config

config.ssh_configure("./pyro4tunneling.json")

logging.basicConfig(level=logging.DEBUG)
t = Pyro4Tunnel('host', ns_port=50000)
bs = t.get_remote_object("BasicServer")
print(type(bs))
print(bs.square(2))
