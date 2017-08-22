## Pyro4 Tunneling

Access Pyro4 objects sitting on remote servers.

### Installation

```bash
/path/to/pyro4tunneling/$> python setup.py install
```
### Usage

The first thing is to launch the nameserver/server on the remote machine.
In the commandline:

```bash
me@remote:/path/to/pyro4tunneling/$> pyro4-ns &
me@remote:/path/to/pyro4tunneling/$> python examples/basic_pyro4_server.py # pass with -nsp to specify namserver port
```

Now, with the 'BasicServer' running on port 50001 on the remote machine,
we can access it locally.

```python
me@local: python
>>> from pyro4tunneling import Pyro4Tunnel
>>> t = Pyro4Tunnel(remote_server_name='remote', remote_port=22, ns_port=9090, remote_username="me")
>>> basic_server = t.get_remote_object('BasicServer')
>>> basic_server.square(2)
4
```

#### Configuration

Let's say that you get tired of writing in the ssh details for a remote machine. `pyro4tunneling` has a few ways of
dealing with this. The first is to add the remote server details to your `~/.ssh/config` file.
This requires no further configuration; `pyro4tunneling` automatically looks in this file to extract ssh configuration information.

You can also provide dictionary or JSON file configurations. A dictionary configuration looks like the following:

```python
from pyro4tunneling import config, Pyro4Tunnel

config.ssh_configure({'remote': ["hostname", "myname", 22]})

tunnel = Pyro4Tunnel('remote',ns_port=9090)
proxy = tunnel.get_remote_object("BasicServer")
```

A JSON file configurations looks like the following:

```python
# json_config.py
from pyro4tunneling import config, Pyro4Tunnel

config.ssh_configure("./pyro4tunneling.json")

tunnel = Pyro4Tunnel('remote',ns_port=9090)
proxy = tunnel.get_remote_object("BasicServer")

```

```json
// pyro4tunneling.json. Note that most parsers won't read comments.
{"remote":["hostname", "username", 22]}
```

See the examples directory for more information.
