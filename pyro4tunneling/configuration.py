from __future__ import print_function
import json
import os
import re
import logging

from . import module_logger

config_logger = logging.getLogger(module_logger.name+".config")

class Configuration(object):

    __slots__ = ('hosts')

    def __init__(self):

        self.hosts = {}
        self.ssh_default_configure()

    def ssh_default_configure(self):
        """
        Look in ~/.ssh/config for hosts.
        Returns:
            None: Updates self.hosts
        """
        ssh_config_path = os.path.join(os.path.expanduser("~"), ".ssh/config")
        if os.path.exists(ssh_config_path):
            with open(ssh_config_path, 'r') as f_config:
                ssh_config = f_config.read()
            pattern = re.compile("host (.*)\n")
            hosts = {match:[] for match in re.findall(pattern, ssh_config)}
            config_logger.debug("ssh_default_configure: Hosts: {}".format(hosts))
            self.hosts.update(hosts)
        else:
            config_logger.debug("ssh_default_configure: No ~/.ssh/config file found.")

    def ssh_configure(self, config):
        """
        Args:
            config (str or dict): Path to configuration file
        Returns:
            None: Updates self.hosts
        """
        if isinstance(config, dict):
            self.hosts.update(config)
        elif isinstance(config, str):
            config_file_path = config
            with open(config_file_path, 'r') as config_file:
                try:
                    hosts = json.load(config_file)
                    self.hosts.update(hosts)
                except Exception as err:
                    config_logger.error("Couldn't load JSON file: {}".format(err))

config = Configuration()
