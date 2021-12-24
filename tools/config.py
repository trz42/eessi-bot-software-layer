import configparser

from .logging import error

_config = {}

def read_file(path):
    """
    Read a given configuration file.
    """
    global _config
    _config = configparser.ConfigParser()
    try:
        _config.read(path)
    except Exception as e:
        print(e)
        error(f'Unable to read configuration file {path}!')


def get_section(name):
    if name in _config:
        return _config[name]
    else:
        return {}
