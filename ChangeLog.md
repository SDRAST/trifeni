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
