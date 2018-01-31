"""
Module for accessing Pyro4 objects in a truly remote fashion.

Author Dean Shaff
"""
from __future__ import print_function
import logging

__version__ = "2.0.0a"

module_logger = logging.getLogger(__name__)

from .configuration import config
from .pyro4tunnel import *
