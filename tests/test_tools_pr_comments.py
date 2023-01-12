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
def raise_exception():
    with patch('github.PullRequest.PullRequest') as mock_pr:
        instance = mock_pr.return_value
        instance.get_issue_comments.side_effect = Exception()
        instance.get_issue_comments.return_value = ()
        instance.get_issue_comment.side_effect = Exception()
        instance.get_issue_comment.return_value = None
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


def test_get_comment_exception(raise_exception):
    with pytest.raises(Exception):
        expected = None
        actual = get_comment(raise_exception, "bar")
        assert expected == actual


def test_get_comment_all_in_one(pr_no_comments, pr_single_comment, raise_exception):
    # no comments exist
    expected = None
    actual = get_comment(pr_no_comments, "foo")
    assert expected == actual

    # search string should be found
    expected = MockIssueComment("foo").body
    actual = get_comment(pr_single_comment, "foo").body
    assert expected == actual

    # search string should not be found
    expected = None
    actual = get_comment(pr_single_comment, "bar")
    assert expected == actual

    # calling get_issue_comments raises an Exception
    with pytest.raises(Exception):
        expected = None
        actual = get_comment(raise_exception, "bar")
        assert expected == actual


def test_get_submitted_job_comment_exception(raise_exception):
    with pytest.raises(Exception):
        expected = None
        actual = get_submitted_job_comment(raise_exception, 42)
        assert expected == actual


# test cases:
#  - comment exists, update is added once to body
#  - comment exists, update is added multiple times to body
#  - comment exists, updating body fails
#  - comment does not exist, edit should not be called
#  - comment does not exist, edit is called, an exception should be raised
#  - get_issue_comment returns an object that has no edit method
def test_update_comment(pr_single_comment):
    # comment exists, update is added once to body
    expected = MockIssueComment("foo updated_once").body
    update_comment(0, pr_single_comment, " updated_once")
    actual = pr_single_comment.get_issue_comment(0).body
    assert expected == actual
