# This file is part of the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#
import re
import sys

from pyghee.utils import log


def get_bot_command(line):
    """
        Retrieve bot command from a line.
    Args:
        line (string): string that is scanned for a command

    Returns:
        command (string): the command if any found or None
    """
    fn = sys._getframe().f_code.co_name

    log(f"{fn}(): searching for bot command in '{line}'")
    match = re.search('^bot: (.*)$', line)
    if match:
        return match.group(1).rstrip()
    else:
        return None
