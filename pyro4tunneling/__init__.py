"""
Module for accessing Pyro4 objects in a truly remote fashion.

Author Dean Shaff
"""
from __future__ import print_function
import logging
import time
import re
import os
import json

import Pyro4

logging.basicConfig(level=logging.DEBUG)
module_logger = logging.getLogger("tunneling")
config_file_path = os.path.join(os.path.expanduser("~"), "./.pyro4tunneling.cfg.json")
if not os.path.exists(config_file_path):
    try:
        os.utime(config_file_path, None)
    except OSError:
        with open(config_file_path, 'a') as config_file:
            config_file.write("null")

def ssh_host_configure(config):
    """
    Set the ssh host configuration. The config_file should
    be a JSON file with host name, host port and remote username information.
    """
    if ".json" not in config:
        raise RuntimeError("Configuration files should be in JSON format")
    with open(config, 'r') as config_file:
        configuration = json.load(config_file)
    return configuration

configuration = ssh_host_configure(config_file_path)
