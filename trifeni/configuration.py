from __future__ import print_function
import json
import os
import re
import logging

from . import module_logger

config_logger = logging.getLogger(module_logger.name+".config")

class Configuration(object):

    __slots__ = ("hosts", "default_identity_file")

    def __init__(self):

        self.default_identity_file = os.path.join(os.path.expanduser("~"), ".ssh/id_rsa")
        self.hosts = {}
        self.ssh_default_configure()

    def ssh_default_configure(self):
        """
        Look in ~/.ssh/config for hosts.
        This then updates the hosts instance attribute with the host information.
        """
        ssh_config_path = os.path.join(os.path.expanduser("~"), ".ssh/config")
        if os.path.exists(ssh_config_path):
            with open(ssh_config_path, 'r') as f_config:
                ssh_config = f_config.read()
            ssh_config_lines = iter(ssh_config.split("\n"))
            hosts = self.get_hosts(ssh_config_lines, {})
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

    def process_host(self, line_iterator, host_dict, host_alias):
        line = next(line_iterator, None)
        if line == "":
            return line_iterator, host_dict
        else:
            split = line.strip().split(" ")
            for key in ["HostName", "Port", "User", "IdentityFile"]:
                if split[0] == key:
                    val = " ".join(split[1:])
                    host_dict[host_alias][key] = val
            return self.process_host(line_iterator, host_dict, host_alias)

    def get_hosts(self, line_iterator, host_dict):
        line = next(line_iterator, None)
        if line is None:
            return host_dict
        else:
            split = line.split(" ")
            if split[0].lower() == "host":
                host_alias = " ".join(split[1:])
                host_dict[host_alias] = {}
                line_iterator, host_dict = self.process_host(line_iterator, host_dict, host_alias)
                if "IdentityFile" in host_dict[host_alias]:
                    identity_file = host_dict[host_alias]["IdentityFile"]
                    host_dict[host_alias]["IdentityFile"] = identity_file.replace("~",os.path.expanduser("~"))
                else:
                    host_dict[host_alias]["IdentityFile"] = self.default_identity_file

            return self.get_hosts(line_iterator, host_dict)


config = Configuration()
