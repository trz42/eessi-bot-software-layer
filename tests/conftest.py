import pytest

def pytest_configure(config):
    # register custom markers
    config.addinivalue_line(
        "markers", "repo_name(name): parametrize test function with a repo name"
    )
    config.addinivalue_line(
        "markers", "pr_number(num): parametrize test function with a PR number"
    )
    config.addinivalue_line(
        "markers", "create_fails(bool): let function create_issue_comment return None"
    )
