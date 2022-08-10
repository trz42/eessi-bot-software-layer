#!/usr/bin/env python3
#
# (Slurm) job manager for the GitHub App for the EESSI project
#
# This tool monitors EESSI build jobs and acts on state changes of
# these jobs. It releases jobs initially held, it processes finished
# jobs and for both reports status changes/results back to the
# corresponding GitHub pull request to a software-layer repo (origin
# or fork).
#
# EESSI build jobs are recognised by
#  - being submitted in JobUserHeld status (sbatch parameter --hold)
#  - job ids listed in a specific directory (ids being symlinks to job
#    directories created by EESSI bot)
#
# author: Kenneth Hoste (@boegel)
# author: Bob Droege (@bedroge)
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#

import configparser
import json
import os
import re
import subprocess
import time

from datetime import datetime, timezone
from connections import github
from tools import args, config

from pyghee.utils import create_file, log


def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)


class EESSIBotSoftwareLayerJobManager:
    'main class for (Slurm) job manager of EESSI bot (separate process)'

    def get_current_jobs(self, poll_command, username):
        squeue_cmd = '%s --long --user=%s' % (poll_command,username)
        log("run squeue command: %s" % squeue_cmd, self.logfile)
        squeue = subprocess.run(squeue_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        log("squeue output\n%s" % squeue.stdout, self.logfile)
        # create dictionary of jobs if any with the following information per job:
        #  jobid, state, nodelist_reason
        # skip first two lines of output ("range(2,...)")
        # TODO check for errors of squeue call
        current_jobs = {}
        lines = str(squeue.stdout,"UTF-8").rstrip().split('\n')
        for i in range(2,len(lines)):
            # assume lines 2 to len(lines) contain jobs
            job = lines[i].rstrip().split()
            if len(job) == 9:
                #print("id %s state %s reason %s" % (job[0], job[4], job[8]))
                current_jobs[job[0]] = { 'jobid' : job[0], 'state' : job[4], 'reason' : job[8] }

        return current_jobs


    #known_jobs = job_manager.get_known_jobs(jobdir)
    def get_known_jobs(self, jobdir):
        # find all symlinks resembling job ids (digits only) in jobdir
        known_jobs = {}
        if os.path.isdir(jobdir):
            regex = re.compile('(\d)+')
            for fname in os.listdir(jobdir):
                if regex.match(fname):
                    full_path = os.path.join(jobdir,fname)
                    if os.path.islink(full_path):
                        known_jobs[fname] = { 'jobid' : fname }
                    else:
                        print("entry %s in %s is not recognised as a symlink" % (full_path,jobdir))
                else:
                    print("entry %s in %s doesn't match regex" % (fname,jobdir))
        else:
            print("directory '%s' does not exist -> assuming no jobs known previously" % jobdir)

        return known_jobs


    #new_jobs = job.manager.determine_new_jobs(known_jobs, current_jobs)
    def determine_new_jobs(self, known_jobs, current_jobs):
        # known_jobs is a dictionary: jobid -> {'jobid':jobid}
        # current_jobs is a dictionary: jobid -> {'jobid':jobid,'state':val,'reason':val}
        new_jobs = []
        for ckey in current_jobs:
            if not ckey in known_jobs:
                new_jobs.append(ckey)

        return new_jobs


    #finished_jobs = job.manager.determine_finished_jobs(known_jobs, current_jobs)
    def determine_finished_jobs(self, known_jobs, current_jobs):
        # known_jobs is a dictionary: jobid -> {'jobid':jobid}
        # current_jobs is a dictionary: jobid -> {'jobid':jobid,'state':val,'reason':val}
        finished_jobs = []
        for kkey in known_jobs:
            if not kkey in current_jobs:
                current_jobs.append(kkey)

        return finished_jobs


    #job_manager.process_new_job(current_jobs[nj])
    def process_new_job(self, new_job, scontrol_command, jobdir):
        # create symlink in jobdir (destination is the working
        #   dir of the job derived via scontrol)
        # release job
        # update PR comment with new status (released)

        # TODO obtain scontrol_command and jobdir from config
        scontrol_cmd = '%s --oneliner show jobid %s' % (
                scontrol_command,
                new_job['jobid'])
        log("run scontrol command: %s" % scontrol_cmd, self.logfile)

        scontrol = subprocess.run(
                scontrol_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)

        # parse output, look for WorkDir=dir
        match = re.search('.* WorkDir=(\S+) .*',
                          str(scontrol.stdout,"UTF-8"))
        if match:
            print("work dir of job %s: '%s'" % (
                new_job['jobid'], match.group(1)))

            symlink_source = os.path.join(jobdir, new_job['jobid'])
            log("create a symlink: %s -> %s" % (
                symlink_source, match.group(1)), self.logfile)
            print("create a symlink: %s -> %s" % (
                symlink_source, match.group(1)))
            os.symlink(match.group(1), symlink_source)

            release_cmd = '%s release jobid %s' % (
                    scontrol_command, new_job['jobid'])
            log("run scontrol command: %s" % release_cmd, self.logfile)
            # TODO uncomment: release = subprocess.run(scontrol_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # update PR
            # (a) get repo name and PR number from file _bot_job<JOBID>.metadata
            # (b) find & get comment for this job
            # (c) add a row to the table

            # (a) get repo name and PR number from file _bot_job<JOBID>.metadata
            #   the file should be written by the event handler to the working dir of the job
            job_metadata_path = '%s/_bot_job%s.metadata' % (
                    match.group(1),
                    new_job['jobid'])
            metadata = configparser.ConfigParser()
            try:
                metadata.read(job_metadata_path)
            except Exception as e:
                print(e)
                error(f'Unable to read job metadata file {job_metadata_path}!')
            # get section
            if 'PR' in metadata:
                metadata_pr = metadata['PR']
            else:
                metadata_pr = {}
            # get repo name
            repo_name = metadata_pr['repo'] or ''
            # get pr number
            pr_number = metadata_pr['pr_number'] or None
            print("pr_number: '%s'" % pr_number)

            print("GH token: expires at '%s'" % github.token().expires_at)

            gh = github.get_instance()

            print("get repo obj for '%s'" % repo_name)
            repo = gh.get_repo(repo_name)
            pr = repo.get_pull(int(pr_number))

            # (b) find & get comment for this job
            # only get comment if we don't know its id yet
            if not 'comment_id' in new_job:
                comments = pr.get_issue_comments()
                for comment in comments:
                    #print("Comment: created at '%s', user '%s', body '%s'" % (
                    #    comment.created_at, comment.user.login, comment.body))

                    # TODO adjust search string to format with more details.
                    cms = '^Job `%s` on `%s`.*' % (
                            new_job['jobid'],
                            config.get_section('github').get('app_name'))

                    comment_match = re.search(cms, comment.body)

                    if comment_match:
                        print("found comment with id %s" % comment.id)
                        new_job['comment_id'] = comment.id
                        break

            # (c) add a row to the table
            # add row to status table if we found a comment
            if 'comment_id' in new_job:
                issue_comment = pr.get_issue_comment(int(new_job['comment_id']))
                original_body = issue_comment.body
                dt = datetime.now(timezone.utc)
                update = '\n|%s|released|Unknown|new symlink `%s`|' % (
                        dt.strftime("%b %d %X %Z %Y"),
                        symlink_source)
                issue_comment.edit(original_body + update)
            else:
                print("did not obtain/find a comment for the job")
                # TODO just create one?
        else:
            # TODO can we run this tool on a job directory? the path to
            #      the directory might be obtained from a comment to the PR
            print("didn't find work dir for job %s" % new_job['jobid'])

        return


    #job_manager.process_finished_job(known_jobs[fj])
    def process_finished_job(self, finished_job):
        # check result (no missing packages, tgz)
        # remove symlink from jobdir
        # update PR comment with new status (finished)
        return


def main():
    """Main function."""
    opts = args.parse()
    config.read_file("app.cfg")
    github.connect()

    job_manager = EESSIBotSoftwareLayerJobManager()
    job_manager.logfile = os.path.join(os.getcwd(), 'eessi_bot_job_manager.log')
    job_manager.job_filter = {}
    if not opts.jobs is None:
        job_manager.job_filter = { jobid : None for jobid in opts.jobs.split(',') }

    # main loop (first sketch)
    #  get status of jobs (user_held,pending,running,"finished")
    #    get list of current jobs (squeue -u ...)
    #    (for now just assume there are non) remove non-bot jobs
    #    compare with known list of known jobs
    #      flag non-existing bot jobs (assumed to have finished) for processing results
    #    (for now assume all new jobs are bot jobs) determine if "new" jobs belong to the bot
    #      flag "new" bot jobs for releasing
    #  process status changes of bot jobs (initial list of states)
    #    unknown -> user_held: release job & update status
    #  configured?
    #    user_held -> pending: update status (queue position)
    #    pending -> running: update status (start time, end time)
    #    running -> finished: update status & provide result summary

    max_iter = int(opts.max_manager_iterations)
    # retrieve some settings from app.cfg
    poll_interval = 0
    poll_command  = 'false'
    job_ids_dir = ''
    if max_iter != 0:
        buildenv = config.get_section('buildenv')
        poll_interval = int(buildenv.get('poll_interval') or 0)
        if poll_interval <= 0:
            poll_interval = 60
        poll_command = buildenv.get('poll_command') or false
        scontrol_command = buildenv.get('scontrol_command') or false
        jobdir = config.get_section('job_manager').get('job_ids_dir')
        mkdir(jobdir)

    # who am i
    username = os.getlogin()

    # max_iter
    #   < 0: run loop indefinitely
    #  == 0: don't run loop
    #   > 0: run loop max_iter times
    # processing may be limited to a list of job ids (see parameter -j --jobs)
    i = 0
    known_jobs = job_manager.get_known_jobs(jobdir)
    while max_iter < 0 or i < max_iter:
        print("\njob manager main loop: iteration %d" % i)
        print("known_jobs='%s'" % known_jobs)

        current_jobs = job_manager.get_current_jobs(poll_command,username)
        print("current_jobs='%s'" % current_jobs)

        new_jobs = job_manager.determine_new_jobs(known_jobs, current_jobs)
        print("new_jobs='%s'" % new_jobs)
        # process new jobs
        for nj in new_jobs:
            if nj in job_manager.job_filter: 
                job_manager.process_new_job(current_jobs[nj], scontrol_command, jobdir)
            else:
                print("skipping job %s due to parameter '--jobs %s'" % (nj,opts.jobs))

        finished_jobs = job_manager.determine_finished_jobs(known_jobs, current_jobs)
        print("finished_jobs='%s'" % finished_jobs)
        # process finished jobs
        for fj in finished_jobs:
            if fj in job_manager.job_filter: 
                job_manager.process_finished_job(known_jobs[fj])
            else:
                print("skipping job %s due to parameter '--jobs %s'" % (fj,opts.jobs))

        known_jobs = current_jobs

        # sleep poll_interval seconds (only if at least one more iteration)
        if max_iter < 0 or i+1 < max_iter:
            print("sleep %d seconds" % poll_interval)
            time.sleep(poll_interval)
        i = i + 1

if __name__ == '__main__':
    main()

