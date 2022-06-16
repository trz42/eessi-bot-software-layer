import json
import os
import subprocess

from connections import github
from tools import config
from pyghee.utils import log
from datetime import datetime


def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def build_easystack_from_pr(pr, event_info):
    # retrieving some settings from 'app.cfg' in bot directory
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
    repo_name = pr.head.repo.full_name
    log("pr.head.repo.full_name '%s'" % pr.head.repo.full_name)
    branch_name = pr.head.ref
    log("pr.head.ref '%s'" % pr.head.ref)

    jobs = []
    for arch_target,slurm_opt in arch_target_map.items():
        arch_job_dir = os.path.join(run_dir, arch_target.replace('/', '_'))
        mkdir(arch_job_dir)
        log("arch_job_dir '%s'" % arch_job_dir)

        # download pull request to arch_job_dir
        #  - PyGitHub doesn't seem capable of doing that (easily);
        #  - for now, keep it simple and just use 'git clone ...'
        #    eg, use 'git clone https://github.com/<repo_name> --branch <branch_name> --single-branch <arch_job_dir>'
        git_clone_cmd = ' '.join([
            'git clone',
            'https://github.com/' + repo_name,
            '--branch ' + branch_name,
            '--single-branch ' + arch_job_dir,
        ])
        log("Clone repo with '%s'" % git_clone_cmd)
        cloned_repo = subprocess.run(git_clone_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        log("Cloned repo!\nStdout %s\nStderr: %s" % (cloned_repo.stdout,cloned_repo.stderr))

        # enlist jobs to proceed
        jobs.append([arch_job_dir,arch_target,slurm_opt])


    log("  %d jobs to proceed after applying white list" % len(jobs))
    if len(jobs) > 0:
        log(json.dumps(jobs, indent=4))

    # Run jobs with the build job submission script
    # Submit functionality should probably moved here at some point, now all part of the Bash script
    for job in jobs:
        cmd = submit_command + ' ' + job[2] + ' ' + build_job_script + ' ' + local_tmp;
        log("Submit job with '%s' from directory '%s'" % (cmd, job[0]))
        submitted_job = subprocess.run(cmd, shell=True, cwd=job[0], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        log("Submit command executed!\nStdout: %s\nStderr: %s" % (submitted_job.stdout, submitted_job.stderr))
