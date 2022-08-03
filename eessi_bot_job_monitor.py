#!/usr/bin/env python3
#
# (Slurm) job monitor for the GitHub App for the EESSI project
#
# This tool monitors jobs and reports back to the corresponding GitHub
# pull request to a software-layer repo (origin or fork).
#
# It essentially monitors the job queue for EESSI (build) jobs and
# acts on state changes of these jobs.
# 
# EESSI (build) jobs are recognised by
#  - being submitted in USER_HELD status (sbatch parameter --hold)
#  - job directory containing a file with a specific name or specific content
#  - job ids listed in a specific directory (ids being symlinks to job
#    directories created by EESSI bot)
#
# Creating lists of ids
#  - at startup, scan specific directory and queue for held jobs
#  - at regular interval, scan specific directory and queue for held jobs
#
# author: Kenneth Hoste (@boegel)
# author: Bob Droege (@bedroge)
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#

#import waitress  # likely won't need to listen on ports
import json
import thread

import pandas as pd

from io import StringIO
from connections import github
from tools import args, config
#from tasks.build import build_easystack_from_pr

from pyghee.lib import read_event_from_json
from pyghee.utils import create_file, log

def process_job_result(pr, event_info, jobid, pr_dir):
    # structure of directory tree
    #   jobs_base_dir/YYYY.MM/pr_<id>/event_<id>/run_<id>/target_<cpuarch>
    #   jobs_base_dir/YYYY.MM/pr_<id>/<jobid> - being a symlink to the job dir
    #   jobs_base_dir/YYYY.MM/pr_<id>/<jobid>/slurm-<jobid>.out

    gh = github.get_instance()

    # seems we have to use `base` here (instead of `head`)
    repo_name = pr.base.repo.full_name
    log("process_job_result: repo_name %s" % repo_name)
    repo = gh.get_repo(repo_name)
    log("process_job_result: pr.number %s" % pr.number)
    pull_request = repo.get_pull(pr.number)

    job_dir = os.path.join(pr_dir,jobid)
    sym_dst = os.readlink(job_dir)
    slurm_out = os.path.join(sym_dst,'slurm-%s.out' % jobid)

    # determine all tarballs that are stored in the job directory (only expecting 1)
    tarball_pattern = 'eessi-*software-*.tar.gz'
    eessi_tarballs = glob.glob(os.path.join(sym_dst,tarball_pattern))

    # set some initial values
    no_missing_modules = False
    targz_created = False

    # check slurm out for the below strings
    #     ^No missing modules!$ --> software successfully installed
    #     ^eessi-2021.12-software-linux-x86_64-intel-haswell-1654294643.tar.gz created!$ --> tarball successfully created
    if os.path.exists(slurm_out):
        re_missing_modules = re.compile('^No missing modules!$')
        re_targz_created = re.compile('^/eessi_bot_job/eessi-.*-software-.*.tar.gz created!$')
        outfile = open(slurm_out, "r")
        for line in outfile:
            if re_missing_modules.match(line):
                # no missing modules
                no_missing_modules = True
            if re_targz_created.match(line):
                # tarball created
                targz_created = True

    if no_missing_modules and targz_created and len(eessi_tarballs) == 1:
        # We've got one tarball and slurm out messages are ok
        # Prepare a message with information such as (installation status, tarball name, tarball size)
        comment = 'SUCCESS The build job (directory %s -> %s) went fine:\n' % (job_dir,sym_dst)
        comment += ' - No missing modules!\n'
        comment += ' - Tarball with size %.3f GiB available at %s.\n' % (os.path.getsize(eessi_tarballs[0])/2**30,eessi_tarballs[0])
        comment += '\nAwaiting approval to ingest this into the repository.\n'
        # report back to PR (just the comment + maybe add a label? (require manual check))
        pull_request.create_issue_comment(comment)
    else:
        # something is not allright:
        #  - no slurm out or
        #  - did not find the messages we expect or
        #  - no tarball or
        #  - more than one tarball
        # prepare a message with details about the above conditions and update PR with a comment
        comment = 'FAILURE The build job (directory %s -> %s) encountered some issues:\n' % (job_dir,sym_dst)
        if not os.path.exists(slurm_out):
            # no slurm out ... something went wrong with the job
            comment += ' - Did not find slurm output file (%s).\n' % slurm_out
        if not no_missing_modules:
            # Found slurm out, but doesn't contain message 'No missing modules!'
            comment += ' - Slurm output file (%s) does not contain pattern: %s.\n' % (slurm_out,re_missing_modules.pattern)
        if not targz_created:
            # Found slurm out, but doesn't contain message 'eessi-.*-software-.*.tar.gz created!'
            comment += ' - Slurm output file (%s) does not contain pattern: %s.\n' % (slurm_out,re_targz_created.pattern)
        if len(eessi_tarballs) == 0:
            # no luck, job just seemed to have failed ...
            comment += ' - No tarball found in %s. (search pattern %s)\n' % (sym_dst,tarball_pattern)
        if len(eessi_tarballs) > 1:
            # something's fishy, we only expected a single tar.gz file
            comment += ' - Found %d tarballs in %s - only 1 expected.\n' % (len(eessi_tarballs),sym_dst)
        comment += '\nIf a tarball has been created, it might still be ok to approve the pull request (e.g., after receiving additional information from the build host).'
        # report back to PR (just the comment + maybe add a label? (require manual check))
        pull_request.create_issue_comment(comment)


class EESSIBotSoftwareLayerJobMonitor:
    'main class for (Slurm) job monitor of EESSI bot (separate process)'

    def get_job_ids(self):

    def check_job_status(self,jobid):


    def handle_issue_comment_event(self, event_info, log_file=None):
        """
        Handle adding/removing of comment in issue or PR.
        """
        request_body = event_info['raw_request_body']
        issue_url = request_body['issue']['url']
        comment_author = request_body['comment']['user']['login']
        comment_txt = request_body['comment']['body']
        log("Comment posted in %s by @%s: %s" % (issue_url, comment_author, comment_txt))
        log("issue_comment event handled!", log_file=log_file)


    def handle_installation_event(self, event_info, log_file=None):
        """
        Handle installation of app.
        """
        request_body = event_info['raw_request_body']
        user = request_body['sender']['login']
        action = request_body['action']
        # repo_name = request_body['repositories'][0]['full_name'] # not every action has that attribute
        log("App installation event by user %s with action '%s'" % (user,action))
        log("installation event handled!", log_file=log_file)


    def handle_pull_request_label_event(self, event_info, pr):
        """
        Handle adding of a label to a pull request.
        """
        log("PR labeled")


    def handle_pull_request_opened_event(self, event_info, pr):
        """
        Handle opening of a pull request.
        """
        log("PR opened")
        build_easystack_from_pr(pr, event_info)


    def handle_pull_request_event(self, event_info, log_file=None):
        """
        Handle 'pull_request' event
        """
        action = event_info['action']
        gh = github.get_instance()
        log("repository: '%s'" % event_info['raw_request_body']['repository']['full_name'] )
        pr = gh.get_repo(event_info['raw_request_body']['repository']['full_name']).get_pull(event_info['raw_request_body']['pull_request']['number'])
        log("PR data: %s" % pr)

        handler_name = 'handle_pull_request_%s_event' % action
        if hasattr(self, handler_name):
            handler = getattr(self, handler_name)
            log("Handling PR action '%s' for PR #%d..." % (action, pr.number))
            handler(event_info, pr)
        else:
            log("No handler for PR action '%s'" % action)


def main():
    """Main function."""
    opts = args.parse()
    config.read_file("app.cfg")
    github.connect()

    if opts.file:
        event = read_event_from_json(opts.file)
        event_info = get_event_info(event)
        handle_event(event_info)
    elif opts.cron:
        log("Running in cron mode")
    else:
        # Run as web app
        app = create_app(klass=EESSIBotSoftwareLayer)
        log("EESSI bot for software layer started!")
        waitress.serve(app, listen='*:%s' % opts.port)

if __name__ == '__main__':
    main()




    # check status for submitted_jobs every N seconds
    poll_interval = int(config.get_section('buildenv').get('poll_interval') or 0)
    if poll_interval <= 0:
        poll_interval = 60
    poll_command = config.get_section('buildenv').get('poll_command')
    # the below method works if the poll command is 'squeue'
    jobs_to_be_checked = submitted_jobs.copy()
    while len(jobs_to_be_checked) > 0:
        # initial pause/sleep
        time.sleep(poll_interval)
        # check status of all jobs_to_be_checked
        #   - handle finished jobs
        #   - update jobs_to_be_checked if any job finished
        job_list_str = ','.join(jobs_to_be_checked)
        # TODO instead of '--long' specify explicitly which columns shall be shown
        squeue_cmd = '%s --long --jobs=%s' % (poll_command,job_list_str)
        log("run squeue command: %s" % squeue_cmd)
        squeue = subprocess.run(squeue_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # cases
        # (1) no job returned -> all finished -> check result for each, update jobs_to_be_checked
        # (2) some/not all jobs returned -> may check status (to detect potential issues), check result for jobs not returned & update jobs_to_be_checked for them
        # (3) all jobs returned -> may check status (to detect potential issues)
        log("squeue output: +++%s+++" % squeue.stdout)
        # TODO add sanity check if any output from command
        job_table = pd.read_csv(StringIO(squeue.stdout.decode("UTF-8")),delim_whitespace=True,skiprows=1)
        if len(job_table) == 0:
            # case (1)
            log("All jobs seem finished.")
            for cj in jobs_to_be_checked:
                log("Processing result of job '%s'." % (cj))
                process_job_result(pr, event_info, cj, os.path.join(jobs_base_dir, ym, pr_id))
            jobs_to_be_checked = []
        elif len(job_table) < len(jobs_to_be_checked):
            # case (2)
            #   set A: finished jobs -> check job result, remove from jobs_to_be_checked
            #   set B: not yet finished jobs -> may check status (to detect potential issues)
            # set A
            jtbc_df = pd.DataFrame(jobs_to_be_checked, columns = ["JOBID"], dtype = int)
            # set A: finished
            finished = jtbc_df[~jtbc_df["JOBID"].isin(job_table["JOBID"])]
            log("Some jobs seem finished: '%s'" % (','.join(finished["JOBID"]).tolist()))
            for fj in finished["JOBID"].tolist():
                log("Processing result of job '%s'." % fj)
                process_job_result(pr, event_info, fj, os.path.join(jobs_base_dir, ym, pr_id))
                jobs_to_be_checked.remove(fj)
            # set B: not yet finished
            not_finished = jtbc_df[jtbc_df["JOBID"].isin(job_table["JOBID"])]
        else:
            # case (3)
            #   not yet finished jobs -> may check status (to detect potential issues)
            log("No job finished yet.")
