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
# author: Lara Ramona Peeters (@laraPPr)
# author: Pedro Santos Neves (@Neves-P)
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#

# Standard library imports
from collections import namedtuple
import configparser
from datetime import datetime, timezone
import json
import os
import shutil
import sys

# Third party imports (anything installed into the local Python environment)
from pyghee.utils import error, log
from retry.api import retry_call

# Local application imports (anything from EESSI/eessi-bot-software-layer)
from connections import github
from tools import config, pr_comments, run_cmd
from tools.job_metadata import create_metadata_file

def move_to_trash_bin(trash_bin_dir, job_dirs):
        move_cmd = ["mv -t", trash_bin_dir]
        for job_dir in job_dirs:
            move_cmd.append(job_dir)
        ' '.join(move_cmd)
        out, err, ec = run_cmd(move_cmd, 'Move job directories to trash_bin', raise_on_error=False)
