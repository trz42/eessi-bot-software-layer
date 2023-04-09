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

from collections import namedtuple
from connections import github
from pyghee.utils import log
from retry import retry
from retry.api import retry_call


PRComment = namedtuple('PRComment', ('repo_name', 'pr_number', 'pr_comment_id'))


@retry(Exception, tries=5, delay=1, backoff=2, max_delay=30)
def get_comment(pr, search_pattern):
    """get comment using the search pattern

    Args:
        pr (object): data of pr
        search_pattern (string): search pattern containing job id

    Returns:
        comment (string): comment for the submitted job
    """
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


def update_comment(cmnt_id, pr, update, log_file=None):
    """update comment of the job

    Args:
        cmnt_id (int): comment id for the submitted job
        pr (object): data of pr
        update (string): updated comment
        log_file (string): path to log file
    """
    issue_comment = retry_call(pr.get_issue_comment, fargs=[cmnt_id], exceptions=Exception,
                               tries=5, delay=1, backoff=2, max_delay=30)
    if issue_comment:
        retry_call(issue_comment.edit, fargs=[issue_comment.body + update], exceptions=Exception,
                   tries=5, delay=1, backoff=2, max_delay=30)
    else:
        log(f"no comment with id {cmnt_id}, skipping update '{update}'",
            log_file=log_file)


def update_pr_comment(event_info, update):
    """
    Updates a comment determined from an event.

    Args:
        event_info (dict): storing all information of an event
        update (string): the update for the comment associated with the event
    """
    request_body = event_info['raw_request_body']
    comment_new = request_body['comment']['body']
    repo_name = request_body['repository']['full_name']
    pr_number = int(request_body['issue']['number'])
    issue_id = int(request_body['comment']['id'])

    gh = github.get_instance()
    repo = gh.get_repo(repo_name)
    pull_request = repo.get_pull(pr_number)
    issue_comment = pull_request.get_issue_comment(issue_id)
    issue_comment.edit(comment_new + update)
