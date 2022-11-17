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

from .logging import error

_config = {}


def read_file(path):
    """
    Read a given configuration file.
    """
    global _config
    try:
        _config = configparser.ConfigParser()
        _config.read_file(path)
    except Exception as e:
        print(e)
        error(f'Unable to read configuration file {path}!')


def get_section(name):
    if name in _config:
        return _config[name]
    else:
        return {}
