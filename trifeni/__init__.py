"""
Module for accessing Pyro4 objects in a truly remote fashion.

Author Dean Shaff
"""
from __future__ import print_function
import logging

__version__ = "2.0.0b"

module_logger = logging.getLogger(__name__)

from .configuration import config
from .util import SSHTunnel, SSHTunnelManager
from .pyro4tunnel import Pyro4Tunnel, DaemonTunnel, NameServerTunnel
from .errors import TunnelError

__all__ = ["config","SSHTunnel", "SSHTunnelManager",
           "Pyro4Tunnel", "DaemonTunnel",
           "NameServerTunnel"]
