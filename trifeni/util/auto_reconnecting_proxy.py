import Pyro4

__all__ = ["AutoReconnectingProxy"]

class AutoReconnectingProxy(Pyro4.core.Proxy):
    """
    A Pyro proxy that automatically recovers from a server disconnect.
    It does this by intercepting every method call and then it first 'pings'
    the server to see if it still has a working connection. If not, it
    reconnects the proxy and retries the method call.
    Drawback is that every method call now uses two remote messages (a ping,
    and the actual method call).
    This uses some advanced features of the Pyro API.
    Taken from Pyro4.examples.
    """
    def _pyroInvoke(self, *args, **kwargs):
        if self._pyroConnection:
            try:
                Pyro4.message.Message.ping(self._pyroConnection, hmac_key=None)    # utility method on the Message class
            except Pyro4.errors.ConnectionClosedError:
                self._pyroReconnect()
        return super(AutoReconnectingProxy, self)._pyroInvoke(*args, **kwargs)
