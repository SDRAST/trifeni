## trifeni

triveni -> تريفيني -> trifeni  

(Used to be pyro4tunneling).

Access Pyro4 objects sitting on remote servers.

### Installation

```bash
/path/to/trifeni/$> python setup.py install
```
### Usage

Say we have some object, `BasicServer`, running with URI `PYRO:BasicServer@localhost:55000`.
(See examples/basic_pyro4_server.py) on a remote (not accessible on the LAN) server.
I might access it as follows:

```python
# example.py
import trifeni

uri = "PYRO:BasicServer@localhost:55000"

with trifeni.DaemonTunnel(remote_server_name="remote") as dt:
    obj_proxy = dt.get_remote_object(uri)
    obj_proxy.square(10)
```

Running this script produces the following output:

```
me@local:/path/to/example/py$ python example.py
>>> 100
```

This example assumes that we have a SSH alias setup with name "remote". The
entry in the ~/.ssh/config file might look as follows:

```
# ~/.ssh.config

host remote
 HostName remote.address
 Port 22
 User me
 IdentityFile ~/.ssh/id_rsa
```

See examples for more information. 

### Testing

Testing can be a little tricky. The tests in `test` assume that you have a ssh
alias "me" setup in your "~/.ssh/config" file. In addition, it assumes that
you don't have anything open and running on ports 9090, 9091, 50000 and 50001.

Once your system is setup, you can run tests as follows:

```
/path/to/trifeni$ python -m unittest discover -s test -t .
```

#### Configuration

Let's say that you get tired of writing in the ssh details for a remote machine. `trifeni` has a few ways of
dealing with this. The first is to add the remote server details to your `~/.ssh/config` file.
This requires no further configuration; `trifeni` automatically looks in this file to extract ssh configuration information.

You can also provide dictionary or JSON file configurations. A dictionary configuration looks like the following:

```python
from trifeni import config, Pyro4Tunnel

config.ssh_configure({'remote': ["hostname", "myname", 22]})

tunnel = Pyro4Tunnel('remote',ns_port=9090)
proxy = tunnel.get_remote_object("BasicServer")
```

A JSON file configurations looks like the following:

```python
# json_config.py
from trifeni import config, Pyro4Tunnel

config.ssh_configure("./trifeni.json")

tunnel = Pyro4Tunnel('remote',ns_port=9090)
proxy = tunnel.get_remote_object("BasicServer")

```

```json
// trifeni.json. Note that most parsers won't read comments.
{"remote":["hostname", "username", 22]}
```

See the examples directory for more information.
