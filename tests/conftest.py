# Configuration of pytest settings for the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#


def pytest_configure(config):
    # register custom markers
    config.addinivalue_line(
        "markers", "repo_name(name): parametrize test function with a repo name"
    )
    config.addinivalue_line(
        "markers", "pr_number(num): parametrize test function with a PR number"
    )
    config.addinivalue_line(
        "markers", "create_raises(string): define function behaviour"
    )
    config.addinivalue_line(
        "markers", "create_fails(bool): let function create_issue_comment return None"
    )
