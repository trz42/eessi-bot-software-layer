# Tests for 'build' task of the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# author: Kenneth Hoste (@boegel)
#
# license: GPLv2
#
import os

from tasks.build import mkdir
from tasks.build import run_cmd
from tasks.build import create_directory


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
    output, exit_code = run_cmd("echo hello", 'test', tmpdir)
    assert output == "hello\n"
    assert exit_code == 0

    output, exit_code = run_cmd("ls -l /does_not_exists.txt", 'fail test', tmpdir)
    assert exit_code != 0





