#!/usr/bin/env python
"""Connects to a remote Cisco VPN using vpnc.

Usage:

    from vpnc import VPNC

    vpn_client = VPNC(config={
        "IPSec_ID": "my IPSec ID",
        "IPSec_gateway": "my.gateway.com",
        "IPSec_secret": "my IPSec secret",
        "Xauth_username": "my Xauth username",
        "Xauth_password": "my Xauth password",
        "IKE_Authmode": "psk",
    })

    with vpn_client.vpn():
        # do stuff on the VPN!

(c) Jack Peterson (jack@tinybike.net), 8/31/2015

"""
from __future__ import print_function

import signal
import sys
import os
import subprocess
from contextlib import contextmanager

HERE = os.path.dirname(os.path.realpath(__file__))


class ProcessException(Exception):
    def __init__(self, returncode, cmd, stdout, stderr):
        self.returncode = returncode
        self.cmd = cmd
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        if self.returncode and self.returncode < 0:
            try:
                return "Command '%s' died with %r." % (
                    self.cmd, signal.Signals(-self.returncode))
            except ValueError:
                return "Command '%s' died with unknown signal %d." % (
                    self.cmd, -self.returncode)
        else:
            return "Command '%s' returned non-zero exit status %d." % (
                self.cmd, self.returncode)


def process_call(cmd):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode:
        raise ProcessException(process.returncode, process.args, stdout, stderr)

    return process.returncode, stdout, stderr


class VPNC(object):

    def __init__(self, config=None,
                 config_file="tempvpnc.conf",
                 config_folder=None):
        self.config = config or dict()
        self.config_file = config_file
        self.temp_config_path = os.path.join(HERE, self.config_file)
        self.config_folder = config_folder
        if config_folder is None:
            if sys.platform.startswith("linux"):
                self.config_folder = "/etc/vpnc"
            elif sys.platform.startswith("darwin"):
                self.config_folder = "/usr/local/etc/vpnc"
        self.config_path = os.path.join(self.config_folder, self.config_file)

    def create_config_file(self):
        """Creates a formatted VPNC config file."""
        with open(self.temp_config_path, "w+") as f:
            print("IPSec gateway %(IPSec_gateway)s\n"
                  "IPSec ID %(IPSec_ID)s\n"
                  "IPSec secret %(IPSec_secret)s\n"
                  "IKE Authmode %(IKE_Authmode)s\n"
                  "Xauth username %(Xauth_username)s\n"
                  "Xauth password %(Xauth_password)s" % self.config,
                  file=f)

    def move_config_file(self):
        """Moves the VPNC config file to /etc/vpnc (Linux) or
        /usr/local/etc/vpnc/ (OSX).
        """
        process_call(["mv", self.temp_config_path, self.config_folder])
        process_call(["chown", "root:root", self.config_path])
        process_call(["chmod", "600", self.config_path])

    def remove_config_file(self):
        """Removes the auto-generated VPNC config file."""
        try:
            process_call(["rm", self.config_path])
            return True
        except subprocess.CalledProcessError:
            return False

    def connect(self):
        """Connects to VPNC."""
        self.create_config_file()
        self.move_config_file()
        process_call(["vpnc", "tempvpnc"])

    def disconnect(self):
        """Disconnects from VPNC."""
        process_call(["vpnc-disconnect"])
        self.remove_config_file()

    @contextmanager
    def vpn(self):
        """Creates VPN context."""
        self.connect()
        yield
        self.disconnect()
