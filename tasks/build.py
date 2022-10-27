import configparser
import json
import os
import subprocess
import time

from connections import github
from datetime import datetime, timezone
from pyghee.utils import log, error
from tools import config

BUILD_JOB_SCRIPT = "build_job_script"
CVMFS_CUSTOMIZATIONS = "cvmfs_customizations"
HTTP_PROXY = "http_proxy"
HTTPS_PROXY = "https_proxy"
JOBS_BASE_DIR = "jobs_base_dir"
LOAD_MODULES = "load_modules"
LOCAL_TMP = "local_tmp"
SLURM_PARAMS = "slurm_params"
SUBMIT_COMMAND = "submit_command"
    

def mkdir(path):
    """create directory on the path passed to the method

    Args:
        path (string): location to where the directory is being created
    """
    if not os.path.exists(path):
        os.makedirs(path)


def get_build_env_cfg():
    """Gets build environment values

    Returns:
         dict(str, dict): dictionary of configuration data
    """
    buildenv = config.get_section('buildenv')

    jobs_base_dir = buildenv.get(JOBS_BASE_DIR)
    log("jobs_base_dir '%s'" % jobs_base_dir)
    config_data = {JOBS_BASE_DIR: jobs_base_dir}
    local_tmp = buildenv.get(LOCAL_TMP)
    log("local_tmp '%s'" % local_tmp)
    config_data[LOCAL_TMP] = local_tmp

    build_job_script = buildenv.get(BUILD_JOB_SCRIPT)
    log("build_job_script '%s'" % build_job_script)
    config_data[BUILD_JOB_SCRIPT] = build_job_script

    submit_command = buildenv.get(SUBMIT_COMMAND)
    log("submit_command '%s'" % submit_command)
    config_data[SUBMIT_COMMAND] = submit_command


    slurm_params = buildenv.get(SLURM_PARAMS)
    # always submit jobs with hold set, so job manager can release them
    slurm_params += ' --hold'
    log("slurm_params '%s'" % slurm_params)
    config_data[SLURM_PARAMS] = slurm_params

    cvmfs_customizations = {}
    try:
        cvmfs_customizations_str = buildenv.get(CVMFS_CUSTOMIZATIONS)
        log("cvmfs_customizations '%s'" % cvmfs_customizations_str)

        if cvmfs_customizations_str != None:
            cvmfs_customizations = json.loads(cvmfs_customizations_str)

        log("cvmfs_customizations '%s'" % json.dumps(cvmfs_customizations))
    except json.decoder.JSONDecodeError as e:
        print(e)
        error(f'Value for cvmfs_customizations ({cvmfs_customizations_str}) could not be decoded.')

    config_data[CVMFS_CUSTOMIZATIONS] = cvmfs_customizations

    http_proxy = buildenv.get(HTTP_PROXY) or ''
    log("http_proxy '%s'" % http_proxy)
    config_data[HTTP_PROXY] = http_proxy

    https_proxy = buildenv.get(HTTPS_PROXY) or ''
    log("https_proxy '%s'" % https_proxy)
    config_data[HTTPS_PROXY] = https_proxy

    load_modules = buildenv.get(LOAD_MODULES) or ''
    log("load_modules '%s'" % load_modules)
    config_data[LOAD_MODULES] = load_modules

    return config_data


def get_architecturetargets():
    """get architecturetargets and set arch_target_map

    Returns:
        dict(str, dict): dictionary of arch_target_map which contains entries of the format OS/SUBDIR : ADDITIONAL_SBATCH_PARAMETERS 
    """
    architecturetargets = config.get_section('architecturetargets')
    arch_target_map = json.loads(architecturetargets.get('arch_target_map'))
    log("arch target map '%s'" % json.dumps(arch_target_map))
    return arch_target_map


def create_directory(pr, jobs_base_dir, event_info):
    """Create directory for Pull Request

    Args:
        pr (object): pr details
        jobs_base_dir (string): location where the bot prepares directories per job
        event_info (string): event received by event_handler 

    Returns:   
        tuple of 3 elements containing

        - ym(string): string with datestamp (<year>.<month>)
        - pr_id(int): pr number
        - run_dir(string): path to run_dir
    """
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
    return ym, pr_id, run_dir


def setup_pr_in_arch_job_dir(repo_name, branch_name, pr, arch_job_dir):
    """Download pull request to arch_job_dir

    Args:
        repo_name (string): pr base repo name
        branch_name (string): pr branch name
        pr (object): pr details
        arch_job_dir (string): location of arch_job_dir
    """
    # download pull request to arch_job_dir
    #  - PyGitHub doesn't seem capable of doing that (easily);
    #  - for now, keep it simple and just execute the commands (anywhere) (note 'git clone' requires that destination is an empty directory)
    #    * patching method
    #      git clone https://github.com/REPO_NAME arch_job_dir
    #      git checkout BRANCH (is stored as ref for base record in PR)
    #      curl -L https://github.com/REPO_NAME/pull/PR_NUMBER.patch > arch_job_dir/PR_NUMBER.patch
    #    (execute the next one in arch_job_dir)
    #      git am PR_NUMBER.patch
    #
    #  - REPO_NAME is repo_name
    #  - PR_NUMBER is pr.number
    git_clone_cmd = ' '.join(['git clone', f'https://github.com/{repo_name}', arch_job_dir])

    log("Clone repo by running '%s' in directory '%s'" % (git_clone_cmd, arch_job_dir))
    cloned_repo = subprocess.run(git_clone_cmd,
                                cwd=arch_job_dir,
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    log("Cloned repo!\nStdout %s\nStderr: %s" % (cloned_repo.stdout, cloned_repo.stderr))

    git_checkout_cmd = ' '.join([
        'git checkout',
        branch_name,
    ])
    log("Checkout branch '%s' by running '%s' in directory '%s'" % (branch_name, git_checkout_cmd, arch_job_dir))
    checkout_repo = subprocess.run(git_checkout_cmd,
                                 cwd=arch_job_dir,
                                 shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
    log("Checked out branch!\nStdout %s\nStderr: %s" % (checkout_repo.stdout, checkout_repo.stderr))

    curl_cmd = f'curl -L https://github.com/{repo_name}/pull/{pr.number}.patch > {pr.number}.patch'

    log("Obtain patch by running '%s' in directory '%s'" % (curl_cmd, arch_job_dir))
    got_patch = subprocess.run(curl_cmd,
                               cwd=arch_job_dir,
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    log("Got patch!\nStdout %s\nStderr: %s" % (got_patch.stdout, got_patch.stderr))

    git_am_cmd = f'git am {pr.number}.patch'
    log("Apply patch by running '%s' in directory '%s'" % (git_am_cmd, arch_job_dir))
    patched = subprocess.run(git_am_cmd,
                             cwd=arch_job_dir,
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    log("Applied patch!\nStdout %s\nStderr: %s" % (patched.stdout, patched.stderr))


def apply_cvmfs_customizations(cvmfs_customizations, arch_job_dir):
    """if cvmfs_customizations are defined then applies it

    Args:
        cvmfs_customizations (dictionary): maps a file name to an entry that needs to be appended to that file. 
        arch_job_dir ((string): location of arch_job_dir
    """
    if len(cvmfs_customizations) > 0:
        # for each entry/key, append value to file
        for key in cvmfs_customizations.keys():
            basename = os.path.basename(key)
            jobcfgfile = os.path.join(arch_job_dir, basename)
            with open(jobcfgfile, "a") as file_object:
                file_object.write(cvmfs_customizations[key]+'\n')

            # TODO (maybe) create mappings_file to be used by
            #      eessi-bot-build.slurm to init SINGULARITY_BIND;
            #      for now, only existing mappings may be customized


def download_pull_request(pr, arch_target_map, run_dir, cvmfs_customizations):
    """setup pull request in arch_job_dir and apply cvmfs customizations

    Args:
        pr (object): data of pr
        arch_target_map (dictionary): contains entries of the format OS/SUBDIR : ADDITIONAL_SBATCH_PARAMETERS where the jobs are submitted 
        run_dir (string): path to run directory
        cvmfs_customizations (dictionary): CVMFS configuration for the build job

    Returns:
        tuple of 2 elements containing
            - repo_name(string):  pr base repository name
            - jobs(list): list containing all the jobs
    """
    # adopting approach outlined in https://github.com/EESSI/eessi-bot-software-layer/issues/17
    # need to use `base` instead of `head` ... don't need to know the branch name
    # TODO rename to base_repo_name?
    repo_name = pr.base.repo.full_name
    log("build_easystack_from_pr: pr.base.repo.full_name '%s'" % pr.base.repo.full_name)
    branch_name = pr.base.ref
    log("build_easystack_from_pr: pr.base.repo.ref '%s'" % pr.base.ref)
    jobs = []
    for arch_target, slurm_opt in arch_target_map.items():
        arch_job_dir = os.path.join(run_dir, arch_target.replace('/', '_'))
        
        mkdir(arch_job_dir)
        log("arch_job_dir '%s'" % arch_job_dir)

        setup_pr_in_arch_job_dir(repo_name, branch_name, pr, arch_job_dir)

        # check if we need to apply local customizations:
        #   is cvmfs_customizations defined? yes, apply it
        apply_cvmfs_customizations(cvmfs_customizations, arch_job_dir)


        # enlist jobs to proceed
        jobs.append([arch_job_dir, arch_target, slurm_opt])
    log("  %d jobs to proceed after applying white list" % len(jobs))
    if jobs:
        log(json.dumps(jobs, indent=4))
    
    return repo_name, jobs


def submit_job(job, submitted_jobs, build_env_cfg, ym, pr_id):
    """Parse job id and submit jobs from directory

    Args:
        job (list): jobs to be submitted
        submitted_jobs (list): jobs submitted
        build_env_cfg (dictionary): build environment data
        ym (string): string with datestamp (<year>.<month>)
        pr_id(int): pr number

    Returns:
        tuple of 2 elements containing
            - job_id(string):  job_id of submitted job
            - symlink(string): symlink from main pr_<ID> dir to job dir (job[0])
    """    
    command_line = ' '.join([
        build_env_cfg[SUBMIT_COMMAND],
        build_env_cfg[SLURM_PARAMS],
        job[2],
        build_env_cfg[BUILD_JOB_SCRIPT],
        '--tmpdir', build_env_cfg[LOCAL_TMP],
    ])
    if build_env_cfg[HTTP_PROXY]:
        command_line += f' --http-proxy {build_env_cfg[HTTP_PROXY]}'
    if build_env_cfg[HTTPS_PROXY]:
        command_line += f' --https-proxy {build_env_cfg[HTTPS_PROXY]}'
    if build_env_cfg[LOAD_MODULES]:
        command_line += f' --load-modules {build_env_cfg[LOAD_MODULES]}'
    # TODO the handling of generic targets requires a bit knowledge about
    #      the internals of building the software layer, maybe ok for now,
    #      but it might be good to think about an alternative
    # if target contains generic, add ' --generic' to command line
    if "generic" in job[1]:
        command_line += ' --generic'
    log("Submit job for target '%s' with '%s' from directory '%s'" % (job[1], command_line, job[0]))
    submitted = subprocess.run(
            command_line,
            shell=True,
            cwd=job[0],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    # sbatch output is 'Submitted batch job JOBID'
    #   parse job id & add it to array of submitted jobs PLUS create a symlink from main pr_<ID> dir to job dir (job[0])
    log(f'build_easystack_from_pr(): sbatch out: {submitted.stdout.decode("UTF-8")}')
    log(f'build_easystack_from_pr(): sbatch err: {submitted.stderr.decode("UTF-8")}')

    job_id = submitted.stdout.split()[3].decode("UTF-8")
    submitted_jobs.append(job_id)
    symlink = os.path.join(build_env_cfg[JOBS_BASE_DIR], ym, pr_id, job_id)
    log(f"jobs_base_dir: {build_env_cfg[JOBS_BASE_DIR]}, ym: {ym}, pr_id: {pr_id}, job_id: {job_id}")

    os.symlink(job[0], symlink)
    log("Submit command executed!\nStdout: %s\nStderr: %s" % (submitted.stdout, submitted.stderr))
    return job_id, symlink


def create_metadata(job, repo_name, pr, job_id):
    """Create metadata file in submission dir

    Args:
        job (list):  jobs to be submitted
        repo_name (string): pr base repository name
        pr (object): data of pr
        job_id (string): job id after parsing
    """
    # create _bot_job<jobid>.metadata file in submission directory
    bot_jobfile = configparser.ConfigParser()
    bot_jobfile['PR'] = { 'repo' : repo_name, 'pr_number' : pr.number }
    bot_jobfile_path = os.path.join(job[0], f'_bot_job{job_id}.metadata')
    with open(bot_jobfile_path, 'w') as bjf:
        bot_jobfile.write(bjf)


def create_pr_comments(job, job_id, app_name, job_comment, pr, repo_name, gh, symlink):
    """create comments for pr

    Args:
        job (list): jobs to be submitted
        job_id (string): job id after parsing
        app_name (string): name of the app
        job_comment (string): comments for jobs status and job release
        pr (object): pr data
        repo_name (string): pr base repo name
        gh (object):github instance
        symlink(string): symlink from main pr_<ID> dir to job dir
    """
    job_comment = f'Job `{job_id}` on `{app_name}`'
    # obtain arch from job[1] which has the format OS/ARCH

    arch_name = '-'.join(job[1].split('/')[1:])
    job_comment += f' for `{arch_name}`'
    job_comment += ' in job dir `%s`\n' % symlink
    job_comment += '|date|job status|comment|\n'
    job_comment += '|----------|----------|------------------------|\n'

    dt = datetime.now(timezone.utc)
    job_comment += f'|{dt.strftime("%b %d %X %Z %Y")}|submitted|job waits for release by job manager|'

    repo = gh.get_repo(repo_name)
    pull_request = repo.get_pull(pr.number)
    pull_request.create_issue_comment(job_comment)


def build_easystack_from_pr(pr, event_info):
    """Build from the pr by fetching data for build environment cofinguration, downloading pr, running jobs and adding comments

    Args:
        pr (object): _description_
        event_info (string): event received by event_handler 
    """
    # retrieving some settings from 'app.cfg' in bot directory
    # [github]
    app_name = config.get_section('github').get('app_name')
    
    # [buildenv]
    build_env_cfg = get_build_env_cfg()
    
    # [architecturetargets]
    arch_target_map = get_architecturetargets()   
    
    # [directory structure]
    ym, pr_id, run_dir = create_directory(pr, build_env_cfg[JOBS_BASE_DIR], event_info)
    gh = github.get_instance()
    
    # [download pull request]
    repo_name, jobs = download_pull_request(pr, arch_target_map, run_dir, build_env_cfg[CVMFS_CUSTOMIZATIONS])
    
    # Run jobs with the build job submission script
    submitted_jobs = []
    job_comment = ''
    for job in jobs:
        # TODO make local_tmp specific to job? to isolate jobs if multiple ones can run on a single node
        job_id, symlink = submit_job(job, submitted_jobs, build_env_cfg, ym, pr_id)

        # create _bot_job<jobid>.metadata file in submission directory
        create_metadata(job, repo_name, pr, job_id)
  
        # report submitted jobs (incl architecture, ...)
        create_pr_comments(job, job_id, app_name, job_comment, pr, repo_name, gh, symlink)
