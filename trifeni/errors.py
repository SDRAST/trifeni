import Pyro4

__all__ = ["TunnelError"]

class TunnelError(Pyro4.errors.CommunicationError):
    pass
