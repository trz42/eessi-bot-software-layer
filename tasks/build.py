import json
import os
import subprocess
import time
import glob
import re

from connections import github
from tools import config
from pyghee.utils import log
from datetime import datetime


def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def build_easystack_from_pr(pr, event_info):
    # retrieving some settings from 'app.cfg' in bot directory
    # [github]
    app_name = config.get_section('github').get('app_name')

    # [buildenv]
    buildenv = config.get_section('buildenv')
    jobs_base_dir = buildenv.get('jobs_base_dir')
    log("jobs_base_dir '%s'" % jobs_base_dir)
    local_tmp = buildenv.get('local_tmp')
    log("local_tmp '%s'" % local_tmp)
    build_job_script = buildenv.get('build_job_script')
    log("build_job_script '%s'" % build_job_script)
    submit_command = buildenv.get('submit_command')
    log("submit_command '%s'" % submit_command)

    # [common_job_params]
    common_job_params = config.get_section('common_job_params')
    slurm_params = common_job_params.get('slurm_params')

    # [architecturetargets]
    arch_target_map = json.loads(config.get_section('architecturetargets').get('arch_target_map'))
    log("arch target map '%s'" % json.dumps(arch_target_map))

    # create directory structure according to alternative described in
    #   https://github.com/EESSI/eessi-bot-software-layer/issues/7
    #   jobs_base_dir/YYYY.MM/pr<id>/event_<id>/run_<id>/target_<cpuarch>
    ym = datetime.today().strftime('%Y.%m')
    pr_id = 'pr_%s' % pr.number
    event_id = 'event_%s' % event_info['id']
    event_dir = os.path.join(jobs_base_dir, ym, pr_id, event_id)
    mkdir(event_dir)

    run = 0
    while os.path.exists(os.path.join(event_dir, 'run_%03d' % run)):
        run += 1
    run_dir = os.path.join(event_dir, 'run_%03d' % run)
    mkdir(run_dir)

    gh = github.get_instance()
    # adopting approach outlined in https://github.com/EESSI/eessi-bot-software-layer/issues/17
    # need to use `base` instead of `head` ... don't need to know the branch name
    repo_name = pr.base.repo.full_name
    log("build_easystack_from_pr: pr.base.repo.full_name '%s'" % pr.base.repo.full_name)

    jobs = []
    for arch_target,slurm_opt in arch_target_map.items():
        arch_job_dir = os.path.join(run_dir, arch_target.replace('/', '_'))
        mkdir(arch_job_dir)
        log("arch_job_dir '%s'" % arch_job_dir)

        # download pull request to arch_job_dir
        #  - PyGitHub doesn't seem capable of doing that (easily);
        #  - for now, keep it simple and just execute the commands (anywhere) (note 'git clone' requires that destination is an empty directory)
        #      git clone https://github.com/REPO_NAME arch_job_dir
        #      curl -L https://github.com/REPO_NAME/pull/PR_NUMBER.patch > arch_job_dir/PR_NUMBER.patch
        #    (execute the next one in arch_job_dir)
        #      git am PR_NUMBER.patch
        #  - REPO_NAME is repo_name
        #  - PR_NUMBER is pr.number
        git_clone_cmd = ' '.join([
            'git clone',
            'https://github.com/' + repo_name,
            arch_job_dir,
        ])
        log("Clone repo by running '%s' in directory '%s'" % (git_clone_cmd,arch_job_dir))
        cloned_repo = subprocess.run(git_clone_cmd,
                                     cwd=arch_job_dir,
                                     shell=True,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
        log("Cloned repo!\nStdout %s\nStderr: %s" % (cloned_repo.stdout,cloned_repo.stderr))

        curl_cmd = 'curl -L https://github.com/%s/pull/%s.patch > %s.patch' % (repo_name,pr.number,pr.number)
        log("Obtain patch by running '%s' in directory '%s'" % (curl_cmd,arch_job_dir))
        got_patch = subprocess.run(curl_cmd,
                                   cwd=arch_job_dir,
                                   shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        log("Got patch!\nStdout %s\nStderr: %s" % (got_patch.stdout,got_patch.stderr))

        git_am_cmd = 'git am %s.patch' % pr.number
        log("Apply patch by running '%s' in directory '%s'" % (git_am_cmd,arch_job_dir))
        patched = subprocess.run(git_am_cmd,
                                 cwd=arch_job_dir,
                                 shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        log("Applied patch!\nStdout %s\nStderr: %s" % (patched.stdout,patched.stderr))

        # enlist jobs to proceed
        jobs.append([arch_job_dir,arch_target,slurm_opt])


    log("  %d jobs to proceed after applying white list" % len(jobs))
    if len(jobs) > 0:
        log(json.dumps(jobs, indent=4))

    # Run jobs with the build job submission script
    submitted_jobs = []
    job_comment = ''
    for job in jobs:
        log("Submit job with '%s %s %s %s %s' from directory '%s'" % (submit_command, slurm_params, job[2], build_job_script, local_tmp, job[0]))
        # TODO make local_tmp specific to job? to isolate jobs if multiple ones can run on a single node
        command_line = ' '.join([
            submit_command,
            slurm_params,
            job[2],
            build_job_script,
            local_tmp,
        ])
        submitted = subprocess.run(command_line, shell=True, cwd=job[0], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # sbatch output is 'Submitted batch job JOBID'
        #   parse job id & add it to array of submitted jobs PLUS create a symlink from main pr_<ID> dir to job dir (job[0])
        job_id = submitted.stdout.split()[3].decode("UTF-8")
        submitted_jobs.append(job_id)
        job_comment += '|%s|submitted|%s|%s|\n' % (job_id,arch_target,job[0])
        log("jobs_base_dir: %s, ym: %s, pr_id: %s, job_id: %s" % (jobs_base_dir,ym,pr_id,job_id))
        os.symlink(job[0], os.path.join(jobs_base_dir, ym, pr_id, job_id))
        log("Submit command executed!\nStdout: %s\nStderr: %s" % (submitted.stdout, submitted.stderr))

    # report submitted jobs (incl architecture, ...)
    comment = 'Submitted %d job(s) on %s\n' % (len(submitted_jobs),app_name)
    if len(submitted_jobs) > 0:
        comment += '|job id|job status|os/architecture|job directory|\n'
        comment += '|------|----------|----------------|------------------------------|\n'
    # repo_name = pr.base.repo.full_name # already set above
    repo = gh.get_repo(repo_name)
    pull_request = repo.get_pull(pr.number)
    pull_request.create_issue_comment(comment+job_comment)
