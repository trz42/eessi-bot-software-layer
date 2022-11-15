# Tests for 'job managaer' task of the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# author: Kenneth Hoste (@boegel)
# author: Hafsa Naeem (@hafsa-naeem)
#
# license: GPLv2
#
import os
from eessi_bot_job_manager import EESSIBotSoftwareLayerJobManager

# from eessi_bot_job_manager import ESSIBotSoftwareLayerJobManager.read_job_pr_metadata


def test_read_job_pr_metadata(tmpdir):
    # if metadata file does not exist, we should get None as return value
    read_job = EESSIBotSoftwareLayerJobManager()
    path = os.path.join(tmpdir, "test.metadata")
    assert read_job.read_job_pr_metadata(path) is None

    with open(path, "w") as fp:
        fp.write(
            """[PR]
        repo=test
        pr_number=12345"""
        )

    metadata_pr = read_job.read_job_pr_metadata(path)
    expected = {
        "repo": "test",
        "pr_number": "12345",
    }
    assert metadata_pr == expected
