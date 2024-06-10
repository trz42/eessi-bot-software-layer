# This file is part of the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# author: Pedro Santos Neves (@Neves-P)
#
# license: GPLv2
#

# Standard library imports
import sys

# Third party imports (anything installed into the local Python environment)
from pyghee.utils import log

# Local application imports (anything from EESSI/eessi-bot-software-layer)
from tools import run_cmd


def move_to_trash_bin(trash_bin_dir, job_dirs):
    funcname = sys._getframe().f_code.co_name
    log(f"{funcname}(): trash_bin_dir = {trash_bin_dir}")

    move_cmd = ["mkdir -p trash_bin_dir && mv -t", trash_bin_dir]
    for job_dir in job_dirs:
        move_cmd.append(job_dir)
        ' '.join(move_cmd)
        out, err, ec = run_cmd(move_cmd, 'Move job directories to trash_bin', raise_on_error=False)

    return
