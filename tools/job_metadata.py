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
from collections import namedtuple
import configparser
import os
import sys

from pyghee.utils import log, error
from tasks.build import Job


def create_metadata_file(job, job_id, pr, pr_comment_id):
    """Create metadata file in submission dir.

    Args:
        job (named tuple): key data about job that has been submitted
        job_id (string): id of submitted job
        pr (github.PullRequest.Pullrequest): object to interact with pull request
        pr_comment_id (int): id of PR comment
    """
    fn = sys._getframe().f_code.co_name

    repo_name = pr.base.repo.full_name

    # create _bot_job<jobid>.metadata file in submission directory
    bot_jobfile = configparser.ConfigParser()
    bot_jobfile['PR'] = {'repo': repo_name, 'pr_number': pr.number, 'pr_comment_id': pr_comment_id}
    bot_jobfile_path = os.path.join(job.working_dir, f'_bot_job{job_id}.metadata')
    with open(bot_jobfile_path, 'w') as bjf:
        bot_jobfile.write(bjf)
    log(f"{fn}(): created job metadata file {bot_jobfile_path}")


def read_metadata_file(job_metadata_path, log_file=None):
    """
    Try to read metadata file and return its PR section. Return None in
    case of failure (treat all cases as if the file did not exist):
    - file does not exist,
    - file exists but does not contain PR section,
    - file exists but parsing/reading resulted in an exception.

    Args:
        job_metadata_path (string): path to job metadata file
        log_file (string): path to log file
    """
    # check if metadata file exist
    if os.path.isfile(job_metadata_path):
        log(f"Found metadata file at {job_metadata_path}", log_file)
        metadata = configparser.ConfigParser()
        try:
            metadata.read(job_metadata_path)
        except Exception as err:
            # error would let the process exist, this is too harsh,
            log(f"Unable to read job metadata file {job_metadata_path}: {err}")
            return None

        # get PR section
        if "PR" in metadata:
            return metadata["PR"]
        else:
            return None
    else:
        log(f"No metadata file found at {job_metadata_path}, so not a bot job", log_file)
        return None
