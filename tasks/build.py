import os
import shutil

from connections import gh

JOBS_DIR = os.path.join(os.getenv('HOME'), 'jobs')
EASYSTACK_PATH = os.path.join('2021-12', '03_workflow', 'yaml-files', 'softwarelist.yaml')
SCRIPTS_DIR = os.path.join(os.getenv('HOME'), 'git', 'hackathons', '2021-12', '03_workflow', 'scripts')


def build_easystack_from_pr(pr, request):
    event_id = request.headers['X-Github-Delivery']
    jobdir = os.path.join(JOBS_DIR, event_id)
    #os.makedirs(jobdir)
    shutil.copytree(SCRIPTS_DIR, jobdir)
    # TODO: checkout the branch that belongs to the PR
    # PyGitHub doesn't seem capable of doing that (easily);
    # for now, keep it simple and just download the easystack file
    repo = gh.get_repo(pr.head.repo.full_name)
    easystack = repo.get_contents(EASYSTACK_PATH, ref=pr.head.ref)
    with open(os.path.join(jobdir, os.path.basename(EASYSTACK_PATH)), 'w') as easystack_file:
        easystack_file.write(easystack.decoded_content.decode('UTF-8'))

