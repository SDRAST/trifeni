import logging

from trifeni import NameServerTunnel, config

config.ssh_configure("./pyro4tunneling.json")

logging.basicConfig(level=logging.DEBUG)
with NameServerTunnel(remote_server_name="host", ns_port=9090) as ns:
    bs = ns.get_remote_object("BasicServer")
    bs.square(2)
