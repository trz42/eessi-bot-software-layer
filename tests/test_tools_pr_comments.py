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
from tools.pr_comments import get_comment, get_submitted_job_comment


class MockIssueComment:
    def __init__(self, body):
        self.body = body


@pytest.fixture
def raise_exception():
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
        instance.get_issue_comments.return_value = (MockIssueComment("foo"),)
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


def test_get_submitted_job_comment_exception(raise_exception):
    with pytest.raises(Exception):
        expected = None
        actual = get_submitted_job_comment(raise_exception, 42)
        assert expected == actual
