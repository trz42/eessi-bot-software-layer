# Tests for 'build' task of the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# author: Kenneth Hoste (@boegel)
# author: Hafsa Naeem (@hafsa-naeem)
# author: Jacob Ziemke (@jacobz137)
#
# license: GPLv2
#

from tools import run_subprocess


def test_run_subprocess(tmpdir):
    """Tests for run_subprocess function."""
    output, err, exit_code = run_subprocess("echo hello", 'test', tmpdir)
    assert exit_code == 0
    assert output == "hello\n"
    assert err == ""

    output, err,  exit_code, = run_subprocess("ls -l /does_not_exists.txt", 'fail test', tmpdir)
    assert exit_code != 0
    assert output == ""
    assert "No such file or directory" in err

    output, err, exit_code = run_subprocess("this_command_does_not_exist", 'fail test', tmpdir)
    assert exit_code != 0
    assert output == ""
    assert ("this_command_does_not_exist: command not found" in err or "this_command_does_not_exist: not found" in err)
