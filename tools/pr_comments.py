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
import time
from tools import logging


def get_comment(pr, search_pattern):
    """get comment using the search pattern

    Args:
        pr (object): data of pr
        search_pattern (string): search pattern containing job id

    Returns:
        comment (string): comment for the submitted job
    """
    tries = 3
    for i in range(tries):
        # If the config keys are not set, get_access_token will raise a NotImplementedError
        # Returning NoneType token will stop the connection in get_instance
        try:
            comments = pr.get_issue_comments()
            for comment in comments:

                cms = f".*{search_pattern}.*"

                comment_match = re.search(cms, comment.body)

                if comment_match:
                    return comment
            break

        except Exception as err:
            if i < tries - 1:
                n = 0.8
                t = n*(i+1)
                time.sleep(t)
                continue
            else:
                logging.error(err)
    return None


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
    tries = 3
    for i in range(tries):
        try:
            job_search_pattern = f"submitted.*job id `{job_id}`"
            break

        except Exception as err:
            if i < tries - 1:
                n = 0.8
                t = n*(i+1)
                time.sleep(t)
                continue
            else:
                logging.error(err)

    return get_comment(pr, job_search_pattern)


def update_comment(cmnt_id, pr, update):
    """update comment of the job

    Args:
        cmnt_id (int): comment id for the submitted job
        pr (object): data of pr
        update (string): updated comment
    """
    tries = 3
    for i in range(tries):
        try:
            issue_comment = pr.get_issue_comment(cmnt_id)
            issue_comment.edit(issue_comment.body + update)
            break

        except Exception as err:
            if i < tries - 1:
                n = 0.8
                t = n*(i+1)
                time.sleep(t)
                continue
            else:
                logging.error(err)
