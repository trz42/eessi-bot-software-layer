# Tests for functions defined in 'tools/pr_comments.py' of the EESSI
# build-and-deploy bot, see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#

# Standard library imports
import os

# Third party imports (anything installed into the local Python environment)
import pytest
from unittest.mock import patch

# Local application imports (anything from EESSI/eessi-bot-software-layer)
from tools.pr_comments import get_comment, get_submitted_job_comment, update_comment


class MockIssueComment:
    def __init__(self, body):
        self.body = body

    def edit(self, body):
        self.body = body


@pytest.fixture
def get_issue_comments_raise_exception():
    with patch('github.PullRequest.PullRequest') as mock_pr:
        instance = mock_pr.return_value
        instance.get_issue_comments.side_effect = Exception()
        instance.get_issue_comments.return_value = ()
        yield instance


@pytest.fixture
def pr_no_comments():
    with patch('github.PullRequest.PullRequest') as mock_pr:
        instance = mock_pr.return_value
        instance.get_issue_comments.return_value = ()
        yield instance


@pytest.fixture
def pr_single_comment():
    with patch('github.PullRequest.PullRequest') as mock_pr:
        instance = mock_pr.return_value
        instance._issue_comments = [MockIssueComment("foo")]
        instance.get_issue_comments.return_value = instance._issue_comments
        # always returns first element. can this depend on the argument
        # provided to the function get_issue_comment?
        instance.get_issue_comment.return_value = instance._issue_comments[0]
        yield instance


# cases:
#  - no comments exist
#  - search string should be found
#  - search string should not be found
#  - calling get_issue_comments raises an Exception
def test_get_comment_no_comment(pr_no_comments):
    expected = None
    actual = get_comment(pr_no_comments, "foo")
    assert expected == actual


def test_get_comment_found(pr_single_comment):
    expected = MockIssueComment("foo").body
    actual = get_comment(pr_single_comment, "foo").body
    assert expected == actual


def test_get_comment_not_found(pr_single_comment):
    expected = None
    actual = get_comment(pr_single_comment, "bar")
    assert expected == actual


def test_get_comment_exception(get_issue_comments_raise_exception):
    with pytest.raises(Exception):
        expected = None
        actual = get_comment(get_issue_comments_raise_exception, "bar")
        assert expected == actual


def test_get_submitted_job_comment_exception(get_issue_comments_raise_exception):
    with pytest.raises(Exception):
        expected = None
        actual = get_submitted_job_comment(get_issue_comments_raise_exception, 42)
        assert expected == actual


# test cases:
#  - pr.get_issue_comment(cmnt_id) succeeds
#    C1: returns obj with edit & body -> edit is called (and succeeds, see C4)
#    C2: returns None -> edit is not called, log message is written
#  - pr.get_issue_comment(cmnt_id) fails (e.g., connection error)
#    . fails 1,...,n times (n > tries) --> should it raise a specific Exception (to indicate
#      that the first command failed)?
#    C3.1 - not implemented yet
#    C3.n
#  - issue_comment.edit(...) succeeds (side effect: body is changed)
#    C4: included in C1
#  - issue_comment.edit(...) fails (connection error, called with incompatible types)
#    . fails 1,...,n times (n > tries) --> should it raise a specific Exception (to indicate
#      that the second command failed)?
#    C5.1 - not implemented yet
#    C5.n
#    C6.1 - not implemented yet
#    C6.n
#
class GetIssueCommentException(Exception):
    "Raised when pr.get_issue_comment fails in a test."
    pass


class EditIssueCommentException(Exception):
    "Raised when issue_comment.edit fails in a test."
    pass


def test_get_issue_comment_succeeds_none(tmpdir):
    log_file = os.path.join(tmpdir, "log.txt")
    with patch('github.PullRequest.PullRequest') as mock_pr:
        instance = mock_pr.return_value
        instance.get_issue_comment.return_value = None

        cmnt_id = 0
        update = "body-0"
        update_comment(cmnt_id, instance, update, log_file=log_file)

        # log_file should exists
        assert os.path.exists(log_file)

        # log_file should contain error message ""
        expected = f"no comment with id {cmnt_id}, skipping update '{update}'"
        file = tmpdir.join("log.txt")
        actual = file.read()
        # actual log message starts with a timestamp, hence we use 'in'
        assert expected in actual


def test_get_issue_comment_succeeds_one_comment(tmpdir):
    log_file = os.path.join(tmpdir, "log.txt")
    comment_to_update = MockIssueComment("__ORG-comment__")
    with patch('github.PullRequest.PullRequest') as mock_pr:
        instance = mock_pr.return_value
        instance.get_issue_comment.return_value = comment_to_update

        cmnt_id = 0
        update = "body-0"
        update_comment(cmnt_id, instance, update, log_file=log_file)

        # log_file should not exists
        assert not os.path.exists(log_file)

        # check body of updated comment
        expected = "__ORG-comment__body-0"
        actual = comment_to_update.body
        assert expected == actual


def test_get_issue_comment_fails(tmpdir):
    log_file = os.path.join(tmpdir, "log.txt")
    with patch('github.PullRequest.PullRequest') as mock_pr:
        instance = mock_pr.return_value
        instance.get_issue_comment.side_effect = GetIssueCommentException

        cmnt_id = -1
        update = "raise GetIssueCommentException"
        with pytest.raises(Exception):
            update_comment(cmnt_id, instance, update, log_file=log_file)

            # log_file should not exists
            assert not os.path.exists(log_file)

            # check if function was retried x times
            expected = 3
            actual = instance.get_issue_comment.call_count
            assert expected == actual


def test_issue_comment_edit_fails_exception(tmpdir):
    log_file = os.path.join(tmpdir, "log.txt")
    comment_to_update = MockIssueComment("__ORG-comment__")
    with patch('github.PullRequest.PullRequest') as mock_pr, \
            patch('tests.test_tools_pr_comments.MockIssueComment') as mock_ic:
        instance_pr = mock_pr.return_value
        instance_pr.get_issue_comment.return_value = comment_to_update
        instance_ic = mock_ic.return_value
        instance_ic.edit.side_effect = EditIssueCommentException

        cmnt_id = 0
        update = "raise EditIssueCommentException"
        with pytest.raises(Exception):
            update_comment(cmnt_id, instance_pr, update, log_file=log_file)

            # log_file should not exists
            assert not os.path.exists(log_file)

            # check that body has not been updated
            expected = "__ORG-comment__"
            actual = comment_to_update.body
            assert expected == actual

            # check if function was retried x times
            expected = 3
            actual = instance_pr.get_issue_comment.call_count
            assert expected == actual

            # check if function was retried x times
            expected = 3
            actual = instance_ic.edit.call_count
            assert expected == actual


def test_issue_comment_edit_fails_args(tmpdir):
    log_file = os.path.join(tmpdir, "log.txt")
    comment_to_update = MockIssueComment("__ORG-comment__")
    with patch('github.PullRequest.PullRequest') as mock_pr, \
            patch('tests.test_tools_pr_comments.MockIssueComment') as mock_ic:
        instance_pr = mock_pr.return_value
        instance_pr.get_issue_comment.return_value = comment_to_update
        instance_ic = mock_ic.return_value

        cmnt_id = 0
        update = 42
        with pytest.raises(Exception):
            update_comment(cmnt_id, instance_pr, update, log_file=log_file)

            # log_file should not exists
            assert not os.path.exists(log_file)

            # check that body has not been updated
            expected = "__ORG-comment__"
            actual = comment_to_update.body
            assert expected == actual

            # check if function was retried x times
            expected = 3
            actual = instance_ic.edit.call_count
            assert expected == actual
