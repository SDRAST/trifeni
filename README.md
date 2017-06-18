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
$> from pyro4tunneling import Pyro4Tunnel
$> t = Pyro4Tunnel('remote')
$> basic_server = t.get_remote_object('BasicServer')
$> basic_server.square(2)
4
```

As of version 0.1.0, the module doesn't clean up ssh connections.
