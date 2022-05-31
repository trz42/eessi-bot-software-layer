import json
import os
import subprocess
import tempfile
#import shutil

from connections import github
from tools import config
from pyghee.utils import log


def build_easystack_from_pr(pr, event_info):
    # retrieving some settings from 'app.cfg' in bot directory
    # [buildenv]
    jobs_base_dir = config.get_section('buildenv').get('jobs_base_dir')
    log("jobs_base_dir '%s'" % (jobs_base_dir))
    scripts_dir = config.get_section('buildenv').get('scripts_dir')
    log("scripts_dir '%s'" % (scripts_dir))
    local_tmp = config.get_section('buildenv').get('local_tmp')
    log("local_tmp '%s'" % (local_tmp))
    build_job_script = config.get_section('buildenv').get('build_job_script')
    log("build_job_script '%s'" % (build_job_script))
    submit_command = config.get_section('buildenv').get('submit_command')
    log("submit_command '%s'" % (submit_command))

    # [softwaretargets]
    # software_file currently not being used (may be later to limit what files will be processed)
    software_file = config.get_section('softwaretargets').get('software_file')
    log("software file '%s'" % (software_file))
    whitelist_versions = json.loads(config.get_section('softwaretargets').get('whitelist_versions'))
    log("whitelisted versions '%s'" % (json.dumps(whitelist_versions)))

    # [architecturetargets]
    arch_target_map = json.loads(config.get_section('architecturetargets').get('arch_target_map'))
    log("arch target map '%s'" % (json.dumps(arch_target_map)))

    # get event id and create main directory for event and a temporary dir
    # inside that (the latter uses mktemp to create a new job every time the
    # event is being redelivered, i.e., useful while developing)
    event_id = event_info['id']
    jobs_dir = os.path.join(jobs_base_dir, event_id)
    if not os.path.exists(jobs_dir):
        os.makedirs(jobs_dir)
    job_run_dir = tempfile.mkdtemp(dir=jobs_dir)
    log("created temporary job run directory '%s'" % (job_run_dir))

    # TODO: checkout the branch that belongs to the PR --> what's actually missing???
    # PyGitHub doesn't seem capable of doing that (easily);
    # for now, keep it simple and just download the easystack file
    gh = github.get_instance()
    repo = gh.get_repo(pr.head.repo.full_name)
    log("pr.head.repo.full_name '%s'" % (pr.head.repo.full_name))
    log("pr.head.ref '%s'" % (pr.head.ref))

    # - determine files to proceed and prepare job dirs (essentially we
    #   may have gotten multiple easystack files (N) via a single PR and
    #   the bot may be configured to build for different
    #   (micro)architectures (M); resulting in N x M jobs)
    # - the N files may be filtered by white listed versions (bot config)
    # - we assume that the full path to the easystack file includes
    #   an EESSI version, e.g., 2021.12/softwarelist.yaml
    jobs = []
    for pr_file in repo.get_pull(pr.number).get_files():
        log("PR file '%s'" % (pr_file.filename))
        stack_version = os.path.dirname(pr_file.filename)
        stack_file = os.path.basename(pr_file.filename)

        for wv in whitelist_versions:
            if wv == stack_version:
                log("  PR file '%s' white listed" % (pr_file.filename))
                easystack = repo.get_contents(pr_file.filename, ref=pr.head.ref)

                # create directory for the "file" (including directory) from PR
                stack_job_dir = os.path.join(job_run_dir, stack_version)
                if not os.path.exists(stack_job_dir):
                    os.makedirs(stack_job_dir)

                for arch_target,slurm_opt in arch_target_map.items():
                    arch_job_dir = os.path.join(stack_job_dir, arch_target.replace("/","_"))
                    if not os.path.exists(arch_job_dir):
                        os.makedirs(arch_job_dir)

                    with open(os.path.join(arch_job_dir, stack_file), 'w') as easystack_file:
                        easystack_file.write(easystack.decoded_content.decode('UTF-8'))

                    # enlist jobs to proceed
                    jobs.append([stack_version,arch_target,slurm_opt,arch_job_dir,stack_file])

    log("  %d jobs to proceed after applying white list" % len(jobs))
    if len(jobs) > 0:
        log(json.dumps(jobs, indent=4))

    # Run jobs the build job submission script
    # Submit functionality should probably moved here at some point, now all part of the Bash script
    for job in jobs:
        log("  Create stack given by '%s'\n    for version '%s'\n    on target '%s'\n    with options '%s'\n    in directory '%s'" % (job[4],job[0],job[1],job[2],job[3]))
        # instead of setting these env variables maybe store these
        # in some '_env' file in the job directory, this (writing
        # into the file '_env') is anyhow done by the batch script
        # and later on '_env' is read by the modified EESSI install
        # script
        d = dict(os.environ)
        d["SOFTWARE_FILE"] = job[4]
        d["SCRIPTS_DIR"] = scripts_dir
        d["LOCAL_TMP"] = local_tmp
        d["BUILD_TARGET_ARCHITECTURE"] = job[1]
        d["BUILD_EESSI_VERSION"] = job[0]
        log("Submit job with '%s %s %s/%s' from directory '%s'" % (submit_command, job[2], scripts_dir, build_job_script, job[3]))
        # alternative to command_line as string would be a list of strings each without a whitespace, e.g.,
        # [submit_command, job[2] /*splitted*/, scripts_dir + '/' + build_job_script]
        command_line = submit_command + ' ' + job[2] + ' ' + scripts_dir + '/' + build_job_script;
        submitted_job = subprocess.run(command_line, shell=True, cwd=job[3], env=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        log("Submit command executed!\nStdout: %s\nStderr: %s" % (submitted_job.stdout, submitted_job.stderr))
