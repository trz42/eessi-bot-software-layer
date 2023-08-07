# This file is part of the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# author: Bob Droege (@bedroge)
#
# license: GPLv2
#

# Standard library imports
import datetime
import os
import sys

# Third party imports (anything installed into the local Python environment)

# Local application imports (anything from EESSI/eessi-bot-software-layer)

# TODO possibly replace 'HOME' (and log file name) with a configurable value
LOG = os.path.join(os.getenv('HOME'), 'eessi-bot-software-layer.log')


def error(msg, rc=1):
    """
    Print an error and exit

    Args:
        msg (string): error message to be printed
        rc (int): error code

    Returns:
        does not return anything (function never returns, but rather exits the
        program)
    """
    sys.stderr.write(msg + "\n")
    sys.exit(rc)


def log(msg):
    """
    Log message

    Args:
        msg (string): error message to be printed

    Returns:
        does not return anything
    """
    with open(LOG, 'a') as fh:
        timestamp = datetime.datetime.now().strftime("%Y%m%d-T%H:%M:%S")
        fh.write('[' + timestamp + '] ' + msg + '\n')
