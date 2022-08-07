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
#  - job ids listed in a specific directory (ids being symlinks to job
#    directories created by EESSI bot)
#
# author: Kenneth Hoste (@boegel)
# author: Bob Droege (@bedroge)
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#

import json
import os
import re
import subprocess
import time

from connections import github
from tools import args, config

from pyghee.utils import create_file, log


class EESSIBotSoftwareLayerJobMonitor:
    'main class for (Slurm) job monitor of EESSI bot (separate process)'

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


    #known_jobs = job_monitor.get_known_jobs(jobdir)
    def get_known_jobs(self, jobdir):
        # find all symlinks resembling job ids (digits only) in jobdir
        known_jobs = {}
        if os.path.isdir(jobdir):
            regex = re.compile('(\d)+')
            for fname in os.listdir(jobdir):
                if regex.match(fname) and os.path.islink(fname):
                    known_jobs[fname] = { 'jobid' : fname }
        else:
            print("directory '%s' does not exist -> assuming no jobs known previously" % jobdir)

        return known_jobs


    #new_jobs = job.monitor.determine_new_jobs(known_jobs, current_jobs)
    def determine_new_jobs(self, known_jobs, current_jobs):
        # known_jobs is a dictionary: jobid -> {'jobid':jobid}
        # current_jobs is a dictionary: jobid -> {'jobid':jobid,'state':val,'reason':val}
        new_jobs = []
        for ckey in current_jobs:
            if not ckey in known_jobs:
                new_jobs.append(ckey)

        return new_jobs


    #finished_jobs = job.monitor.determine_finished_jobs(known_jobs, current_jobs)
    def determine_finished_jobs(self, known_jobs, current_jobs):
        # known_jobs is a dictionary: jobid -> {'jobid':jobid}
        # current_jobs is a dictionary: jobid -> {'jobid':jobid,'state':val,'reason':val}
        finished_jobs = []
        for kkey in known_jobs:
            if not kkey in current_jobs:
                current_jobs.append(kkey)

        return finished_jobs


    #job_monitor.process_new_job(current_jobs[nj])
    def process_new_job(self, new_job):
        return


    #job_monitor.process_finished_job(known_jobs[fj])
    def process_finished_job(self, finished_job):
        return


def main():
    """Main function."""
    opts = args.parse()
    config.read_file("app.cfg")
    github.connect()

    job_monitor = EESSIBotSoftwareLayerJobMonitor()
    job_monitor.logfile = os.path.join(os.getcwd(), 'eessi_bot_job_monitor.log')

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

    max_iter = int(opts.max_monitor_iterations)
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
        jobdir = config.get_section('job_monitor').get('job_ids_dir')

    # who am i
    username = os.getlogin()

    # max_iter
    #   < 0: run loop indefinitely
    #  == 0: don't run loop
    #   > 0: run loop max_iter times
    # TODO should we also have the ability to only process one new job? to ease debugging?
    i = 0
    known_jobs = job_monitor.get_known_jobs(jobdir)
    while max_iter < 0 or i < max_iter:
        print("\njob monitor main loop: iteration %d" % i)
        print("known_jobs='%s'" % known_jobs)
        current_jobs = job_monitor.get_current_jobs(poll_command,username)
        print("current_jobs='%s'" % current_jobs)
        new_jobs = job_monitor.determine_new_jobs(known_jobs, current_jobs)
        print("new_jobs='%s'" % new_jobs)
        # TODO process new jobs
        for nj in new_jobs:
            job_monitor.process_new_job(current_jobs[nj])
        finished_jobs = job_monitor.determine_finished_jobs(known_jobs, current_jobs)
        print("finished_jobs='%s'" % finished_jobs)
        # TODO process finished jobs
        for fj in finished_jobs:
            job_monitor.process_finished_job(known_jobs[fj])

        known_jobs = current_jobs

        # sleep poll_interval seconds (only if at least one more iteration)
        if max_iter < 0 or i+1 < max_iter:
            print("sleep %d seconds" % poll_interval)
            time.sleep(poll_interval)
        i = i + 1

if __name__ == '__main__':
    main()

