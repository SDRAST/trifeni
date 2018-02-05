## Change Log for pyro4tunneling

### Version 1.1

Can pass `local` paramter to `pyrotunneling.Pyro4Tunnel` to make the tunnel object
act like a thin layer over `Pyro4.Proxy`

### Version 1.1.1

- Added version information, stored in `pyro4tunneling.__version__`
- Added `TunnelError` to "exports" in `pyro4tunneling/__init__.py`.

### Version 1.2.0

- Added a `pyro4tunneling.Pyro4Tunnel.cleanup` method that will kill all SSH tunnels
associated with the object.

### Version 1.2.1

- Fixed bug where pyro4tunneling needs ~/.ssh/config to exist.

## Change name to `trifeni`

### Version 2.0.0

- Complete backend and API overhaul, to the point where I considered just
starting a new project.
- Backend changes:
    - Now using `paramiko` instead of `subprocess.Popen` to create tunnels.
- API changes:
    - NameServerTunnel now takes the place of Pyro4Tunnel. There is a
        Pyro4Tunnel class, but this shouldn't be used for attempting to access
        a remote nameserver.
    - Addition of DaemonTunnel that allows for creating tunnels to a Pyro Daemon
        given only a uri.
    - SSH keys are not _required_, but they do make things work a lot better. Without
        SSH keys, `trifeni` will prompt the user for the password to the remote server
        _every time_ it creates a new tunnel. For accessing an object on a remote nameserver
        and setting up a reverse SSH tunnel to a local daemon, this means entering a
        password _three_ times.
