# This file is part of the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# This file implements a class for PR comments.
#
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#

import sys

from pyghee.utils import log


class EESSIBotPRComment:

    def __init__(self, event, github, logfile):
        """
        Init object with pointers to necessary data.
        """
        self.event = event
        self.github = github
        self.logfile = logfile
        self.read_all_information = False
        self.read_key_information = False
        self.issue = {}
        self.sections = {
            'header_config' : { "instance" : "", "targets" : [] },
            'human_readable_log' : [ { "short" : [] }, "full" : [] } ],
            'machine_readable_log' : [],
            'control_room' : [],
        }

    def log(self, msg, *args):
        """
        Logs a message incl the caller's function name by passing msg and *args to PyGHee's log method.

        Args:
            msg (string): message (format) to log to event handler log
            *args (any): any values to be substituted into msg
        """
        funcname = sys._getframe().f_back.f_code.co_name
        if args:
            msg = msg % args
        msg = "[%s]: %s" % (funcname, msg)
        log(msg, log_file=self.logfile)

    def read_key_information_from_event(self):
        """
        Read key information from received event.
        Key information:
            - instance (name)
        """
        self.read_key_information = True

    def read_all_information_from_event(self):
        """
        Read information from received event.
        """
        self.read_all_information = True
        self.read_key_information = True

    def read_key_information_from_config(self, config):
        """
        Read key information from bot config.
        """

    def check_if_comment_concerns_instance(self, instance_name):
        """
        Checks if the comment is for the bot instance_name. Can ignore others.
        """
        if self.read_key_information is False and self.read_all_information is False:
            self.log(f"missing key information to check if comment concerns me (instance {self.instance_name})")
            raise Exception

