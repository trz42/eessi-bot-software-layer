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
import pytest
import subprocess

from eessi_bot_job_manager import EESSIBotSoftwareLayerJobManager

# from eessi_bot_job_manager import ESSIBotSoftwareLayerJobManager.read_job_pr_metadata


@pytest.fixture
def provide_app_cfg():
    # return path to app.cfg?
    return 1


def test_read_job_pr_metadata(tmpdir, provide_app_cfg):
    # copy needed app.cfg from tests directory
    shutil.copyfile("tests/app.cfg", "app.cfg")

    # show contents of current directory
    subprocess.run(["ls", "-l"])

    # if metadata file does not exist, we should get None as return value
    job_manager = EESSIBotSoftwareLayerJobManager()
    path = os.path.join(tmpdir, 'test.metadata')
    assert job_manager.read_job_pr_metadata(path) is None

    with open(path, 'w') as fp:
        fp.write('''[PR]
        repo=test
        pr_number=12345''')

    metadata_pr = job_manager.read_job_pr_metadata(path)
    expected = {
        "repo": "test",
        "pr_number": "12345",
    }
    assert metadata_pr == expected
