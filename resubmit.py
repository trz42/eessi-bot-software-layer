#!/usr/bin/env python3
#
# This file is part of the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# This script resubmits a job with or without changes applied only
# at the local file system where the original job was run. It is also
# updating the PR comment of the original job and enables the job
# manager to pick up the job (including releasing it).
#
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#

import configparser
import glob
import os
import re
import shutil
import subprocess
import sys

from connections import github
from datetime import datetime, timezone
from tools import config
from tools.config import convert_cvmfs_customizations_option
from tools.args import resubmit_parse
from tools.logging import error

from git import Git, Repo
import requests
from typing import Tuple

# constants are defined in tools/config.py
# formatting follows PEP8:
#     see https://peps.python.org/pep-0008/#when-to-use-trailing-commas
REQUIRED_CONFIG = {
    config.SECTION_GITHUB: [
        config.OPTION_PRIVATE_KEY,
    ],
    config.SECTION_BUILDENV: [
        config.OPTION_BUILD_JOB_SCRIPT,
        config.OPTION_CVMFS_CUSTOMIZATIONS,
        config.OPTION_HTTP_PROXY,
        config.OPTION_HTTPS_PROXY,
        config.OPTION_JOBS_BASE_DIR,
        config.OPTION_LOAD_MODULES,
        config.OPTION_LOCAL_TMP,
        config.OPTION_SLURM_PARAMS,
        config.OPTION_SUBMIT_COMMAND,
    ],
    config.SECTION_ARCHITECTURETARGETS: [
        config.OPTION_ARCH_TARGET_MAP,
    ],
}


def determine_last_jobid(directory: str = None) -> int:
    """Determine id of last job run in a directory.

    Args:
        directory (str): path of directory; if not provided, the name
                         of the current directory is used
    Returns:
        jobid (int): id of the last job run in a directory
    """
    fn = sys._getframe().f_code.co_name

    if directory is None:
        directory = os.getcwd()

    # TODO make sure that directory exists and is accessible?

    # Possible sources for file names containing a job id:
    # - _bot_job<JOBID>.metadata file(s)
    # - slurm-<JOBID>.out file(s)
    glob_metadata = '_bot_job[0-9]*.metadata'
    metadata_files = glob.glob(os.path.join(directory, glob_metadata))

    glob_slurm_out = 'slurm-[0-9]*.out'
    slurm_out_files = glob.glob(os.path.join(directory, glob_slurm_out))

    job_ids = [int(re.sub("(.*_bot_job)|(.metadata)", "", jobid)) for jobid in metadata_files] + \
              [int(re.sub("(.*slurm-)|(.out)", "", jobid)) for jobid in slurm_out_files]

    # Determine last jobid (in most cases there will be just one
    # job per directory).
    org_job_id = None
    if len(job_ids) > 0:
        org_job_id = sorted(job_ids, reverse=True)[0]

    print(f"{fn}(): last job id ....: {org_job_id}")
    return org_job_id


def get_pull_request_info(jobid: int, directory: str) -> Tuple[str, int]:
    """Determine name of repository and pull request number from
       a previous job.

    Args:
        jobid (int): id of a previous job
        directory (string): path of a previous job

    Returns:
        Tuple of
        - string: name of the repository
        - int: pull request number
    """
    fn = sys._getframe().f_code.co_name

    # TODO check if there exists a better function for reading the metadata
    job_metadata_file = f"_bot_job{jobid}.metadata"
    job_metadata_path = os.path.join(directory, job_metadata_file)
    metadata = configparser.ConfigParser()
    try:
        metadata.read(job_metadata_path)
    except Exception as e:
        print(e)
        error(f"{fn}(): Unable to read job metadata file {job_metadata_path}!")

    repo_name = None
    pr_number = None
    if "PR" in metadata:
        metadata_pr = metadata["PR"]
        repo_name = metadata_pr.get("repo", None)
        pr_number = metadata_pr.get("pr_number", None)

    print(f"{fn}(): repository name.: '{repo_name}'")
    print(f"{fn}(): pr number ......: '{pr_number}'")
    return repo_name, pr_number


def get_arch_info(jobid: int, directory: str) -> Tuple[str, str, str]:
    """Determine architecture, OS and job params from a previous job.

    Args:
        jobid (int): id of a previous job
        directory (string): path of a previous job

    Returns:
        Tuple of
        - string: architecture name
        - string: operating system name
        - string: Slurm job submission parameters
    """
    fn = sys._getframe().f_code.co_name

    # TODO check if there exists a better function for reading the metadata
    job_metadata_file = f"_bot_job{jobid}.metadata"
    job_metadata_path = os.path.join(directory, job_metadata_file)
    metadata = configparser.ConfigParser()
    try:
        metadata.read(job_metadata_path)
    except Exception as e:
        print(e)
        error(f"{fn}(): Unable to read job metadata file {job_metadata_path}!")

    arch_name = None
    os_name = None
    slurm_opt = None
    if "ARCH" in metadata:
        metadata_arch = metadata["ARCH"]
        arch_name = metadata_arch.get("architecture", None)
        os_name = metadata_arch.get("os", None)
        slurm_opt = metadata_arch.get("slurm_opt", None)

    print(f"{fn}(): archictecture ..: '{arch_name}'")
    print(f"{fn}(): operating system: '{os_name}'")
    print(f"{fn}(): job params .....: '{slurm_opt}'")
    return arch_name, os_name, slurm_opt


def obtain_pull_request(repository_name: str,
                        branch_name: str,
                        pr: object,
                        directory: str) -> bool:
    """Obtain pull request contents to (re-run) directory.

    Args:
        repository_name (string): pr base repository name
        branch_name (string): pr branch name
        pr (object): PullRequest object (PyGithub) representing
                     a pull request.
        directory (string): location to store pr contents in

    Returns:
        result (bool): True if successful, False otherwise
    """
    fn = sys._getframe().f_code.co_name

    # TODO check if directory already exists
    # clone repo
    repo_url = f"https://github.com/{repository_name}"
    cloned_repo = Repo.clone_from(url=repo_url, to_path=directory)
    assert cloned_repo.__class__ is Repo
    print(f"{fn}(): Cloned repo '{repo_url}' into '{directory}'.")

    git = Git(directory)

    # checkout base branch
    # TODO check status
    print(f"{fn}(): Checking out base branch: '{branch_name}'")
    status, co_out, co_err = git.checkout(branch_name, with_extended_output=True)
    print(f"{fn}(): Checked out branch: status {status}, out '{co_out}', err '{co_err}'")

    # optain patch for pull request
    # TODO check status (getting patch & writing file)
    patch_file = f"{pr.number}.patch"
    patch_url = f"{repo_url}/pull/{patch_file}"
    r = requests.get(patch_url)
    patch_target = os.path.join(directory, patch_file)
    with open(patch_target, 'w') as p:
        p.write(r.text)
    print(f"{fn}(): Stored patch under '{patch_target}'")

    # apply patch
    status, am_out, am_err = git.am(patch_target, with_extended_output=True)
    print(f"{fn}(): Applied patch: status {status}, out '{am_out}', err '{am_err}'")

    return (status == 0)


def remove_prefix(path: str, prefix: str) -> str:
    """Removes a prefix from a path.

    Args:
        path (string): a path
        prefix (string): a prefix

    Returns:
       path (string): returns path-prefix or path
    """
    if path.startswith(prefix):
        return path[len(prefix):]
    else:
        return path


def copy_contents(source_directory: str, target_directory: str) -> bool:
    """Copy contents from source to target.

    Args:
        source_directory (string): path to source directory
        target_directory (string): path to target directory

    Returns:
        result (bool): True if successful, False otherwise
    """
    for root, _dirs, files in os.walk(source_directory):
        # path = root.split(os.sep)
        # base = os.path.basename(root)
        # dirname = os.path.dirname(root)

        rel_target = remove_prefix(root, source_directory).strip('/')
        todir = os.path.join(target_directory, rel_target).rstrip('/')

        if root != source_directory:
            if os.path.isdir(root):
                os.makedirs(todir, exist_ok=True)

        for f in files:
            src = os.path.join(root, f)
            if os.path.islink(src):
                linkto = os.readlink(src)
                linkfrom = os.path.join(todir, f)
                os.symlink(linkto, linkfrom)
            else:
                shutil.copy(src, todir)

    return True


def get_original_job_dir(opts):
    """Get directory of original job.

    Args:
        opts (object): parsed command line arguments

    Returns:
        directory (string): original job dir
    """
    fn = sys._getframe().f_code.co_name

    original_job_dir = None
    if opts.original_job_dir is not None:
        original_job_dir = opts.original_job_dir
    else:
        original_job_dir = os.getcwd()
    print(f"{fn}(): returning directory '{original_job_dir}'")

    return original_job_dir


def get_rerun_job_dir(original_job_dir):
    """Determine name of directory to re-run the job from.

    Args:
        original_job_dir (string): directory of original job

    Returns:
        directory (string): name of the re-run directory
    """
    fn = sys._getframe().f_code.co_name

    # TODO handle case that all 3-digit rerun dirs exist already.
    run = 0
    while os.path.exists(os.path.join(original_job_dir, 'rerun_%03d' % run)):
        run += 1
    rerun_job_dir = os.path.join(original_job_dir, 'rerun_%03d' % run)
    print(f"{fn}(): rerun job dir ..: '{rerun_job_dir}'")
    return rerun_job_dir


def find_comment(pull_request, search_pattern):
    """Find comment in pull request that contains search_pattern.

    Args:
        pull_request (object): PullRequest object (PyGithub) representing
                               a pull request.
        search_pattern (string): String to identify a comment.

    Returns:
        issue_comment (object): IssueComment object (PyGithub) representing
                                an issue comment or None if none found.
    """
    comments = pull_request.get_issue_comments()
    for comment in comments:
        cms = f".*{search_pattern}.*"
        comment_match = re.search(cms, comment.body)
        if comment_match:
            return comment
    return None


def run_cmd(cmd, working_dir=None):
    """Runs a command in the shell

    Args:
        cmd (string): command to run
        working_dir (string): directory to run cmd in

    Returns:
        result (object): subprocess.CompletedProcess
    """
    fn = sys._getframe().f_code.co_name

    if working_dir is None:
        working_dir = os.getcwd()

    print(f"{fn}(): Running '{cmd}' in directory '{working_dir}'")

    result = subprocess.run(cmd,
                            cwd=working_dir,
                            shell=True,
                            encoding="UTF-8",
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    if result.returncode != 0:
        status = "ERROR"
    else:
        status = "SUCCESS"

    log_msg = (f"{fn}(): {status} running '{cmd}' in '{working_dir}'\n"
               f"           stdout '{result.stdout}'\n"
               f"           stderr '{result.stderr}'\n"
               f"           exit code {result.returncode}")
    print(log_msg)

    return result


def submit_job(job, cfg, ym, pr):
    """Submit job.

    Args:
        job (list): job to be submitted defined by list
                    [arch_job_dir, arch_target, slurm_opt]
        cfg (dictionary): bot configuration
        ym (string): string with datestamp (<year>.<month>)
        pr (object): PullRequest object (PyGithub) representing
                     a pull request.

    Returns:
        tuple of 2 elements containing
            - job_id (string):  job_id of submitted job
            - symlink (string): symlink from main pr_<ID> dir to job dir (job[0])
    """
    fn = sys._getframe().f_code.co_name

    buildenv = cfg[config.SECTION_BUILDENV]
    command_line = " ".join([
        buildenv[config.OPTION_SUBMIT_COMMAND],
        buildenv[config.OPTION_SLURM_PARAMS],
        job[2],
        buildenv[config.OPTION_BUILD_JOB_SCRIPT],
        "--tmpdir", buildenv[config.OPTION_LOCAL_TMP],
    ])
    if buildenv[config.OPTION_HTTP_PROXY] is not None:
        command_line += f" --http-proxy {buildenv[config.OPTION_HTTP_PROXY]}"
    if buildenv[config.OPTION_HTTPS_PROXY] is not None:
        command_line += f" --https-proxy {buildenv[config.OPTION_HTTPS_PROXY]}"
    if buildenv[config.OPTION_LOAD_MODULES] is not None:
        command_line += f" --load-modules {buildenv[config.OPTION_LOAD_MODULES]}"
    # TODO the handling of generic targets requires a bit knowledge about
    #      the internals of building the software layer, maybe ok for now,
    #      but it might be good to think about an alternative
    # if target contains generic, add ' --generic' to command line

    if "generic" in job[1]:
        command_line += ' --generic'

    # submit job, result is of type subprocess.CompletedProcess
    submit = run_cmd(command_line, working_dir=job[0])

    # if successful sbatch output is 'Submitted batch job JOBID'
    if submit.returncode != 0:
        # some ERROR happened, log and exit (leave directory for inspection)
        error(f"{fn}(): sbatch failed; exiting with code 3", rc=3)
    else:
        job_id = submit.stdout.split()[3]
        symlink = os.path.join(buildenv[config.OPTION_JOBS_BASE_DIR], ym, pr.number, job_id)
        print(f"{fn}(): symlinking {symlink} -> {job[0]}")
        os.symlink(job[0], symlink)

    return job_id, symlink


def main():
    """Main function."""
    fn = sys._getframe().f_code.co_name

    now = datetime.now(timezone.utc)

    # parse command-line args
    opts = resubmit_parse()

    # determine directory of original job (current or given as argument)
    original_job_dir = get_original_job_dir(opts)

    # determine id of previous job
    org_job_id = determine_last_jobid(original_job_dir)
    if org_job_id is None:
        # directory seems to not contain a job, exiting
        error(f"{fn}(): did not find any previous job in '{original_job_dir}'")

    # determine location of app config file (app.cfg)
    # - assume that the file is in the directory of this script
    # TODO should we have a command line argument for this one?
    app_cfg_dir = os.path.dirname(os.path.realpath(__file__))
    app_cfg = os.path.join(app_cfg_dir, 'app.cfg')
    print(f"{fn}(): app.cfg ........: '{app_cfg}'")

    # old method to read configuration is needed for accessing
    #   private key when making connection to github
    config.read_file(app_cfg)

    # read config file to make required options available
    cfg = config.read_and_validate_config(app_cfg, REQUIRED_CONFIG, log_file=sys.stdout)

    # determine name of directory to re-run the job from
    rerun_job_dir = get_rerun_job_dir(original_job_dir)

    # get repo name and pr number from metadata file
    # TODO check if repo_name and pr_number are not None
    repo_name, pr_number = get_pull_request_info(org_job_id, original_job_dir)

    # connect to github and init objects to repo and pull request
    gh = github.get_instance()
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(int(pr_number))
    base_ref = pr.base.ref

    # get original PR, patch and apply patch (similar method used by
    #     event handler) + do customizations (cvmfs, ...)
    if not obtain_pull_request(repo_name, base_ref, pr, rerun_job_dir):
        error(f"{fn}(): failed to obtain pull request", rc=-2)

    # check if we need to apply local customizations:
    #   is cvmfs_customizations defined? yes, apply it
    # TODO (maybe) create mappings_file to be used by
    #      eessi-bot-build.slurm to init SINGULARITY_BIND;
    #      for now, only existing mappings may be customized
    cvmfs_customizations_str = cfg[config.SECTION_BUILDENV][config.OPTION_CVMFS_CUSTOMIZATIONS]
    cvmfs_customizations = convert_cvmfs_customizations_option(cvmfs_customizations_str, log_file=sys.stdout)
    if len(cvmfs_customizations) > 0:
        # for each entry/key, append value to file
        for key in cvmfs_customizations.keys():
            basename = os.path.basename(key)
            jobcfgfile = os.path.join(rerun_job_dir, basename)
            with open(jobcfgfile, "a") as file_object:
                file_object.write(cvmfs_customizations[key] + '\n')

    # The directory modified_job_dir is used as input for
    #   possible changes to the original job. All content of
    #   modified_job_dir is simply copied into rerun_job_dir.
    if opts.modified_job_dir is not None:
        copy_contents(opts.modified_job_dir, rerun_job_dir)

    # get arch_name, os_name and slurm_opt from metadata file
    arch_name, os_name, slurm_opt = get_arch_info(org_job_id, original_job_dir)

    # prepare & create new metadata file (after submission: TEMP -> jobid)
    bot_jobfile = configparser.ConfigParser()
    bot_jobfile["PR"] = {"repo": repo_name, "pr_number": pr.number}
    bot_jobfile["ARCH"] = {"architecture": arch_name, "os": os_name, "slurm_opt": slurm_opt}
    bot_jobfile_path = os.path.join(rerun_job_dir, "_bot_jobTEMP.metadata")
    with open(bot_jobfile_path, 'w') as bjf:
        bot_jobfile.write(bjf)

    # find PR comment (old job id, appname from app.cfg) and update it
    comment = find_comment(pr, f"submitted.*job id `{org_job_id}`")
    if comment is None:
        print(f"{fn}(): found NO PR comment for previous job {org_job_id}")
    else:
        print(f"{fn}(): found PR comment {comment.id} for previous job {org_job_id}")

    # create symlink, update PR comment
    # prepare metadata file --> after submission, just rename it
    # create _bot_job<jobid>.metadata file in submission directory
    ym = now.strftime("%Y.%m")
    print(f"{fn}(): Submit job for target '{arch_name}' from directory '{rerun_job_dir}'")
    job_id, symlink = submit_job([rerun_job_dir, os_name, slurm_opt], cfg, ym, pr)

    # rename job metadata file
    new_metadata_path = bot_jobfile_path.replace('TEMP', job_id, 1)
    os.rename(bot_jobfile_path, new_metadata_path)

    # create symlink from jobs_base_dir/YYYY.MM/pr_PR_NUMBER to
    #   rerun_job_dir
    jobs_base_dir = cfg[config.SECTION_BUILDENV][config.OPTION_JOBS_BASE_DIR]
    pr_id = f"pr_{pr.number}"
    symlink = os.path.join(jobs_base_dir, ym, pr_id, job_id)
    os.symlink(rerun_job_dir, symlink)

    # update PR comment with
    #   'date | resubmitted | jobid + directory'
    #     --> update method in job manager to find comment
    if comment is not None:
        print(f"{fn}(): updating comment with id {comment.id}")
        update = (f"\n|{now.strftime('%b %d %X %Z %Y')}|resubmitted"
                  f"|job id `{job_id}`, dir `{symlink}` awaits release by job manager|")
        comment.edit(comment.body + update)


if __name__ == "__main__":
    main()
