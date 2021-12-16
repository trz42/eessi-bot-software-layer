import configparser

from .logging import error

CONFIG = {}

def read_file(path):
    """
    Read a given configuration file.
    """
    global CONFIG
    CONFIG = configparser.ConfigParser()
    try:
        CONFIG.read(path)
    except Exception as e:
        print(e)
        error(f'Unable to read configuration file {path}!')


def get_section(name):
    if name in CONFIG:
        return CONFIG[name]
    else:
        return {}

#CONFIG = parse_config('../test.cfg')
