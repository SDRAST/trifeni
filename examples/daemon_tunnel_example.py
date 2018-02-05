# daemon_tunnel_example.py
"""
Example showing how to use the DaemonTunnel to create an SSH tunnel to an
object sitting on a remote server. This uses the daemon's URI on the remote
server.

Note that I use "remote_alias" as argument for remote_server_name. This
corresponds to some SSH config alias that's sitting on my "~/.ssh/config".

For this example, I'm assuming you've got a "BasicServer" instance running on
the remote server (see basic_pyro4_server.py)
"""
import Pyro4

import trifeni

uri = "PYRO:BasicServer@localhost:55000"

# We can use the with statement to make sure that the tunnels get destroyed
# responsibly. If not, we _have_ to call shutdown on the DaemonTunnel object.

with trifeni.DaemonTunnel(remote_server_name="remote_alias") as dt:
    obj_proxy = dt.get_remote_object(uri)
    print(obj_proxy.square(10))

# Without the with statement we have to do the following:

dt = trifeni.DaemonTunnel(remote_server_name="remote_alias")
obj_proxy = dt.get_remote_object(uri)
obj_proxy.square(10)
dt.shutdown()

# Using a custom Pyro4.Proxy subclass

class MyProxy(Pyro4.core.Proxy):
    pass

with trifeni.DaemonTunnel(remote_server_name="remote_alias") as dt:
    obj_proxy = dt.get_remote_object(uri, proxy_class=MyProxy)
    obj_proxy.square(1e4)

# There are situations where it's useful to create a reverse tunnel from the
# remote server to the local one, so the server can access methods that
# are registered locally. Obviously the following example is a little overkill,
# but it might be useful to use callbacks when calling methods that take a long
# time to call (longer than the timeout of the server).

import threading

class Callbacks(object):

    @Pyro4.expose
    def some_callback(self, res):
        print(res)
        # do something with res

callbacks = Callbacks()
fresh_daemon = Pyro4.Daemon()
fresh_daemon_uri = fresh_daemon.register(callbacks)
daemon_thread = threading.Thread(target=fresh_daemon.requestLoop)
daemon_thread.daemon = True
daemon_thread.start()

with trifeni.DaemonTunnel(remote_server_name="remote_alias") as dt:
    dt.register_remote_daemon(fresh_daemon)
    obj_proxy = dt.get_remote_object(uri, proxy_class=MyProxy)
    obj_proxy.square_with_callback(100, callback_info={
        "handler": Pyro4.Proxy(fresh_daemon_uri)
        "callback_name": "some_callback"
    })
