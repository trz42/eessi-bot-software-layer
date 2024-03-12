# This file is part of the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# author: Bob Droege (@bedroge)
# author: Kenneth Hoste (@boegel)
# author: Hafsa Naeem (@hafsa-naeem)
# author: Jacob Ziemke (@jacobz137)
# author: Jonas Qvigstad (@jonas-lq)
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#

# Standard library imports
import configparser
import sys

# Third party imports (anything installed into the local Python environment)
# (none yet)

# Local application imports (anything from EESSI/eessi-bot-software-layer)
from .logging import error


def read_config(path='app.cfg'):
    """
    Read the config file

    Args:
        path (string): path to the configuration file

    Returns:
        dict (str, dict): dictionary containing configuration settings or exit
            if Exception is caught
    """
    fn = sys._getframe().f_code.co_name

    try:
        config = configparser.ConfigParser()
        config.read(path)
    except Exception as err:
        error(f"{fn}(): Unable to read configuration file {path}!\n{err}")

    return config


def check_required_cfg_settings(req_settings, path="app.cfg"):
    """
    Reads the config file, checks if it contains the required settings,
    if not logs an error message and exits.

    Args:
        req_settings (dict (str, list)): required settings
        path (string): path to the configuration file

    Returns:
        None (implicitly)
    """
    # TODO argument path is not being used
    cfg = read_config()
    # iterate over keys in req_settings which correspond to sections ([name])
    # in the configuration file (.ini format)
    for section in req_settings.keys():
        if section not in cfg:
            error(f'Missing section "{section}" in configuration file {path}.')
        # iterate over list elements required for the current section
        for item in req_settings[section]:
            if item not in cfg[section]:
                error(f'Missing configuration item "{item}" in section "{section}" of configuration file {path}.')
