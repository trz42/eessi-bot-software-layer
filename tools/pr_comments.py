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


def get_comment(pr, search_pattern):
    """_summary_

    Args:
        pr (object): data of pr
        search_pattern (string): search pattern containing job id

    Returns:
        comment (sting): comment for the submitted job
    """
    comments = pr.get_issue_comments()
    for comment in comments:
        # NOTE adjust search string if format changed by event
        #        handler (separate process running
        #        eessi_bot_event_handler.py)
        cms = f".*{search_pattern}.*"

        comment_match = re.search(cms, comment.body)

        if comment_match:
            return comment
    return None


def get_submitted_job_comment(pr, job_id):
    """_summary_

    Args:
        pr (object): data of pr
        job_id (string): job id of submitted job

    Returns:
        tuple of 2 elements containing

        - pr (object): data of pr
        - job_search_pattern(string): search pattern containing job id
    """
    job_search_pattern = f"submitted.*job id `{job_id}`"
    return get_comment(pr, job_search_pattern)


def update_comment(cmnt_id, pr, update):
    """_summary_

    Args:
        cmnt_id (int): comment id for the submitted job
        pr (object): data of pr
        update (string): updated comment
    """
    issue_comment = pr.get_issue_comment(int(cmnt_id))
    issue_comment.edit(issue_comment.body + update)
