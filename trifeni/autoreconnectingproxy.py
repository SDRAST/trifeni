import Pyro4

from . import module_logger

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
        # We override the method that does the actual remote calls: _pyroInvoke.
        # If there's still a connection, try a ping to see if it is still alive.
        # If it isn't alive, reconnect it. If there's no connection, simply call
        # the original method (it will reconnect automatically).
        if self._pyroConnection:
            try:
                # print("  <proxy: ping>")
                Pyro4.message.Message.ping(self._pyroConnection, hmac_key=None)    # utility method on the Message class
                # print("  <proxy: ping reply (still connected)>")
            except Pyro4.errors.ConnectionClosedError:
                # print("  <proxy: Connection lost. REBINDING...>")
                self._pyroReconnect()
                # print("  <proxy: Connection restored, continue with actual method call...>")
        return super(AutoReconnectingProxy, self)._pyroInvoke(*args, **kwargs)
