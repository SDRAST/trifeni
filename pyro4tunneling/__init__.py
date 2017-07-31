"""
Module for accessing Pyro4 objects in a truly remote fashion.

Author Dean Shaff
"""
from __future__ import print_function
import logging

__version__ = "1.1.1.2"

module_logger = logging.getLogger(__name__)

from .configuration import config
from .pyro4tunnel import Pyro4Tunnel, TunnelError
