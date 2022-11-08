# Tests for 'build' task of the EESSI build-and-deploy bot,
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

from tasks.build import mkdir
from tasks.build import run_cmd


def test_mkdir(tmpdir):
    """Tests for mkdir function."""
    test_dir = os.path.join(tmpdir, 'test')
    mkdir(test_dir)
    assert os.path.isdir(test_dir)

    # parent directories are created if needed
    deep_test_dir = os.path.join(tmpdir, 'one', 'two', 'three')
    assert not os.path.exists(os.path.dirname(os.path.dirname(deep_test_dir)))
    mkdir(deep_test_dir)
    assert os.path.isdir(deep_test_dir)

    # calling mkdir on an existing path is fine (even if that path is a file?!)
    mkdir(test_dir)
    assert os.path.isdir(test_dir)
    test_file = os.path.join(tmpdir, 'test.txt')
    with open(test_file, 'w') as fp:
        fp.write('')

    mkdir(test_file)
    assert os.path.isfile(test_file)


def test_run_cmd(tmpdir):
    """Tests for run_cmd function."""
    output, err, exit_code = run_cmd("echo hello", 'test', tmpdir)
    assert exit_code == 0
    assert output == "hello\n"
    assert err == ""

    output, err,  exit_code, = run_cmd("ls -l /does_not_exists.txt", 'fail test', tmpdir)
    assert exit_code != 0
    assert output == ""
    assert "No such file or directory" in err

    output, err, exit_code = run_cmd("this_command_does_not_exist", 'fail test', tmpdir)
    assert exit_code != 0
    assert output == ""
    assert ("this_command_does_not_exist: command not found" in err or "this_command_does_not_exist: not found" in err)

