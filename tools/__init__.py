# This file is part of the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# author: Kenneth Hoste (@boegel)
# author: Bob Droege (@bedroge)
# author: Hafsa Naeem (@hafsa-naeem)
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#
import os
import subprocess

from pyghee.utils import log


def run_cmd(cmd, log_msg='', working_dir=None):
    """Runs a command in the shell

    Args:
        cmd (string): command to run
        log_msg (string): purpose of the command
        working_dir (string): location of arch_job_dir

    Returns:
        tuple of 3 elements containing
        - stdout (string): stdout of the process
        - stderr (string): stderr of the process
        - exit_code (string): exit code of the process
    """
    if working_dir is None:
        working_dir = os.getcwd()

    if log_msg:
        log(f"run_cmd(): '{log_msg}' by running '{cmd}' in directory '{working_dir}'")
    else:
        log(f"run_cmd(): Running '{cmd}' in directory '{working_dir}'")

    result = subprocess.run(cmd,
                            cwd=working_dir,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    stdout = result.stdout.decode("UTF-8")
    stderr = result.stderr.decode("UTF-8")
    exit_code = result.returncode

    if exit_code != 0:
        log(f"run_cmd(): Error running '{cmd}' in '{working_dir}\n"
            f"           stdout '{stdout}'\n"
            f"           stderr '{stderr}'\n"
            f"           exit code {exit_code}")
    else:
        log(f"run_cmd(): Result for running '{cmd}' in '{working_dir}\n"
            f"           stdout '{stdout}'\n"
            f"           stderr '{stderr}'\n"
            f"           exit code {exit_code}")

    return stdout, stderr, exit_code
