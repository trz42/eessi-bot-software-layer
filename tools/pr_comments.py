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
import re

from pyghee.utils import log
from retry import retry


@retry(Exception, tries=5, delay=1, backoff=2, max_delay=30)
def get_comment(pr, search_pattern):
    """get comment using the search pattern

    Args:
        pr (object): data of pr
        search_pattern (string): search pattern containing job id

    Returns:
        comment (string): comment for the submitted job
    """
    # If the config keys are not set, get_access_token will raise a NotImplementedError
    # Returning NoneType token will stop the connection in get_instance
    comments = pr.get_issue_comments()
    for comment in comments:
        cms = f".*{search_pattern}.*"
        comment_match = re.search(cms, comment.body)
        if comment_match:
            return comment

    return None


# Note, no @retry decorator used here because it is already used with get_comment.
def get_submitted_job_comment(pr, job_id):
    """get comment of the submitted job id

    Args:
        pr (object): data of pr
        job_id (string): job id of submitted job

    Returns:
        tuple of 2 elements containing

        - pr (object): data of pr
        - job_search_pattern(string): search pattern containing job id
    """
    # NOTE adjust search string if format changed by event
    #      handler (separate process running
    #      eessi_bot_event_handler.py)
    job_search_pattern = f"submitted.*job id `{job_id}`"
    return get_comment(pr, job_search_pattern)


@retry(Exception, tries=5, delay=1, backoff=2, max_delay=30)
def update_comment(cmnt_id, pr, update, log_file=None):
    """update comment of the job

    Args:
        cmnt_id (int): comment id for the submitted job
        pr (object): data of pr
        update (string): updated comment
        log_file (string): path to log file
    """
    issue_comment = pr.get_issue_comment(cmnt_id)
    if issue_comment:
        issue_comment.edit(issue_comment.body + update)
    else:
        log(f"no comment with id {cmnt_id}, skipping update '{update}'", log_file=log_file)
