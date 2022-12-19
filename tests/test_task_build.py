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

from tools import run_cmd, run_subprocess


def test_run_cmd(tmpdir):
    """Tests for run_cmd function."""
    log_file = os.path.join(tmpdir, "log.txt")
    output, err, exit_code = run_cmd("echo hello", 'test', tmpdir, log_file=log_file)

    assert exit_code == 0
    assert output == "hello\n"
    assert err == ""

    output, err,  exit_code = run_cmd("ls -l /does_not_exists.txt", 'fail test', tmpdir, log_file=log_file)

    assert exit_code != 0
    assert output == ""
    assert "No such file or directory" in err

    output, err, exit_code = run_cmd("this_command_does_not_exist", 'fail test', tmpdir, log_file=log_file)

    assert exit_code != 0
    assert output == ""
    assert ("this_command_does_not_exist: command not found" in err or "this_command_does_not_exist: not found" in err)

    output, err, exit_code = run_cmd("echo hello", "test in file", tmpdir, log_file=log_file)
    with open(log_file, "r") as fp:
        assert "test in file" in fp.read()


def test_run_subprocess(tmpdir):
    """Tests for run_subprocess function."""
    log_file = os.path.join(tmpdir, "log.txt")
    output, err, exit_code = run_subprocess("echo hello", 'test', tmpdir, log_file=log_file)

    assert exit_code == 0
    assert output == "hello\n"
    assert err == ""

    output, err, exit_code = run_subprocess("ls -l /does_not_exists.txt", 'fail test', tmpdir, log_file=log_file)

    assert exit_code != 0
    assert output == ""
    assert "No such file or directory" in err

    output, err, exit_code = run_subprocess("this_command_does_not_exist", 'fail test', tmpdir, log_file=log_file)

    assert exit_code != 0
    assert output == ""
    assert ("this_command_does_not_exist: command not found" in err or "this_command_does_not_exist: not found" in err)

    output, err, exit_code = run_subprocess("echo hello", "test in file", tmpdir, log_file=log_file)
    with open(log_file, "r") as fp:
        assert "test in file" in fp.read()
