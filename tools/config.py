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
import configparser
import sys

from .logging import error


def read_config(path='app.cfg'):
    """Read the config file
    Args:
        path (string): path to the configuration file
    Returns:
        dict (str, dict): dictionary containing configuration settings
    """
    fn = sys._getframe().f_code.co_name

    try:
        config = configparser.ConfigParser()
        config.read(path)
    except Exception:
        error(f"{fn}(): Unable to read configuration file {path}!")

    return config
