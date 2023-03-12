# Tests for 'build' task of the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# author: Kenneth Hoste (@boegel)
# author: Hafsa Naeem (@hafsa-naeem)
# author: Jacob Ziemke (@jacobz137)
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#

import filecmp
import os
import pytest

from tools import run_cmd, run_subprocess
from tasks.build import Job, create_metadata_file


def test_run_cmd(tmpdir):
    """Tests for run_cmd function."""
    log_file = os.path.join(tmpdir, "log.txt")
    output, err, exit_code = run_cmd("echo hello", 'test', tmpdir, log_file=log_file)

    assert exit_code == 0
    assert output == "hello\n"
    assert err == ""

    with pytest.raises(Exception):
        output, err, exit_code = run_cmd("ls -l /does_not_exists.txt", 'fail test', tmpdir, log_file=log_file)

        assert exit_code != 0
        assert output == ""
        assert "No such file or directory" in err

    output, err, exit_code = run_cmd("ls -l /does_not_exists.txt",
                                     'fail test',
                                     tmpdir,
                                     log_file=log_file,
                                     raise_on_error=False)

    assert exit_code != 0
    assert output == ""
    assert "No such file or directory" in err

    with pytest.raises(Exception):
        output, err, exit_code = run_cmd("this_command_does_not_exist", 'fail test', tmpdir, log_file=log_file)

        assert exit_code != 0
        assert output == ""
        assert ("this_command_does_not_exist: command not found" in err or
                "this_command_does_not_exist: not found" in err)

    output, err, exit_code = run_cmd("this_command_does_not_exist",
                                     'fail test',
                                     tmpdir,
                                     log_file=log_file,
                                     raise_on_error=False)

    assert exit_code != 0
    assert output == ""
    assert ("this_command_does_not_exist: command not found" in err or
            "this_command_does_not_exist: not found" in err)

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


# def test_create_pr_comment(tmpdir):
#     """Tests for function create_pr_comment."""


def test_create_metadata_file(tmpdir):
    """Tests for function create_metadata_file."""
    # create some test data
    job = Job(tmpdir, "test/architecture", "--speed_up_job")
    job_id = "123"
    repo_name = "test_repo"
    pr_number = 999
    pr_comment_id = 77
    create_metadata_file(job, job_id, repo_name, pr_number, pr_comment_id)

    expected_file = f"_bot_job{job_id}.metadata"
    expected_file_path = os.path.join(tmpdir, expected_file)
    # assert expected_file exists
    assert os.path.exists(expected_file_path)

    # assert file contents =
    # [PR]
    # repo = test_repo
    # pr_number = 999
    # pr_comment_id = 77
    test_file = "tests/test_bot_job123.metadata"
    assert filecmp.cmp(expected_file_path, test_file, shallow=False)

    # use directory that does not exist
    dir_does_not_exist = os.path.join(tmpdir, "dir_does_not_exist")
    job2 = Job(dir_does_not_exist, "test/architecture", "--speed_up_job")
    job_id2 = "222"
    with pytest.raises(FileNotFoundError):
        create_metadata_file(job2, job_id2, repo_name, pr_number, pr_comment_id)

    # use directory without write permission
    dir_without_write_perm = os.path.join("/")
    job3 = Job(dir_without_write_perm, "test/architecture", "--speed_up_job")
    job_id3 = "333"
    with pytest.raises(OSError):
        create_metadata_file(job3, job_id3, repo_name, pr_number, pr_comment_id)

    # disk quota exceeded (difficult to create and unlikely to happen because
    # partition where file is stored is usually very large)

    # use undefined values for parameters
    # job_id = None
    job4 = Job(tmpdir, "test/architecture", "--speed_up_job")
    job_id4 = None
    create_metadata_file(job4, job_id4, repo_name, pr_number, pr_comment_id)

    expected_file4 = f"_bot_job{job_id}.metadata"
    expected_file_path4 = os.path.join(tmpdir, expected_file4)
    # assert expected_file exists
    assert os.path.exists(expected_file_path4)

    # assert file contents =
    test_file = "tests/test_bot_job123.metadata"
    assert filecmp.cmp(expected_file_path4, test_file, shallow=False)

    # use undefined values for parameters
    # job.working_dir = None
    job5 = Job(None, "test/architecture", "--speed_up_job")
    job_id5 = "555"
    with pytest.raises(TypeError):
        create_metadata_file(job5, job_id5, repo_name, pr_number, pr_comment_id)
