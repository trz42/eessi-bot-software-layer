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
import glob
import os
import re
import subprocess
import time

from connections import github
from datetime import datetime, timezone
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
                current_jobs[job[0]] = { 'jobid' : job[0], 'state' : job[4], 'reason' : job[8] }

        return current_jobs


    #known_jobs = job_manager.get_known_jobs(submitted_jobs_dir)
    def get_known_jobs(self, submitted_jobs_dir):
        # find all symlinks resembling job ids (digits only) in jobdir
        known_jobs = {}
        if os.path.isdir(submitted_jobs_dir):
            regex = re.compile('(\d)+')
            for fname in os.listdir(submitted_jobs_dir):
                if regex.match(fname):
                    full_path = os.path.join(submitted_jobs_dir,fname)
                    if os.path.islink(full_path):
                        known_jobs[fname] = { 'jobid' : fname }
                    else:
                        print("entry %s in %s is not recognised as a symlink" % (full_path,submitted_jobs_dir))
                else:
                    print("entry %s in %s doesn't match regex" % (fname,submitted_jobs_dir))
        else:
            print("directory '%s' does not exist -> assuming no jobs known previously" % submitted_jobs_dir)

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
                finished_jobs.append(kkey)

        return finished_jobs


    #job_manager.process_new_job(current_jobs[nj])
    def process_new_job(self, new_job, scontrol_command, submitted_jobs_dir):
        # create symlink in submitted_jobs_dir (destination is the working
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

            symlink_source = os.path.join(submitted_jobs_dir, new_job['jobid'])
            log("create a symlink: %s -> %s" % (
                symlink_source, match.group(1)), self.logfile)
            print("create a symlink: %s -> %s" % (
                symlink_source, match.group(1)))
            os.symlink(match.group(1), symlink_source)

            release_cmd = '%s release %s' % (
                    scontrol_command, new_job['jobid'])
            log("run scontrol command: %s" % release_cmd, self.logfile)
            print("run scontrol command: %s" % release_cmd)
            release = subprocess.run(release_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("scontrol out: %s" % release.stdout.decode("UTF-8"))
            print("scontrol err: %s" % release.stderr.decode("UTF-8"))

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
                    # NOTE adjust search string if format changed by event
                    #        handler (separate process running
                    #        eessi_bot_software_layer.py)
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
                update = '\n|%s|released|symlk `%s`|' % (
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
        # check result
        #   ("No missing packages!", "eessi-.*.tar.gz")
        #   TODO as is, this requires knowledge about the build process.
        #          maybe better to somehow capture job "result" (process
        #          exit value) by build script?
        # update PR comment with new status (finished)
        # move symlink from job_ids_dir/submitted to jobs_ids_dir/finished

        # 'submitted_jobs_dir'/jobid is symlink to working dir of job
        #  working dir contains _bot_job<jobid>.metadata
        #    file contains (pr number and base repo name)

        # establish contact to pull request on github
        gh = github.get_instance()

        # set some variables for accessing work dir of job
        job_manager = config.get_section('job_manager')
        job_ids_dir = job_manager.get('job_ids_dir')
        submitted_jobs_dir = os.path.join(job_ids_dir,'submitted')
        job_dir = os.path.join(submitted_jobs_dir, finished_job['jobid'])
        sym_dst = os.readlink(job_dir)

        # TODO create function for obtaining values from metadata file
        #        might be based on allowing multiple configuration files
        #        in tools/config.py
        metadata_file = '_bot_job%s.metadata' % finished_job['jobid']
        job_metadata_path = os.path.join(job_dir,metadata_file)

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

        repo = gh.get_repo(repo_name)
        pull_request = repo.get_pull(int(pr_number))

        # determine comment to be updated
        if not 'comment_id' in finished_job:
            comments = pull_request.get_issue_comments()
            for comment in comments:
                # NOTE adjust search string if format changed by event
                #        handler (separate process running
                #        eessi_bot_software_layer.py)
                cms = '^Job `%s` on `%s`.*' % (
                        finished_job['jobid'],
                        config.get_section('github').get('app_name'))

                comment_match = re.search(cms, comment.body)

                if comment_match:
                    print("found comment with id %s" % comment.id)
                    finished_job['comment_id'] = comment.id
                    break

        # analyse job result
        slurm_out = os.path.join(sym_dst,'slurm-%s.out' % finished_job['jobid'])

        # determine all tarballs that are stored in the job directory (only expecting 1)
        tarball_pattern = 'eessi-*software-*.tar.gz'
        glob_str = os.path.join(sym_dst,tarball_pattern)
        eessi_tarballs = glob.glob(glob_str)

        # set some initial values
        no_missing_modules = False
        targz_created = False

        # check slurm out for the below strings
        #   ^No missing modules!$ --> software successfully installed
        #   ^/eessi_bot_job/eessi-.*-software-.*.tar.gz created!$ --> tarball successfully created
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

        dt = datetime.now(timezone.utc)

        if no_missing_modules and targz_created and len(eessi_tarballs) == 1:
            # We've got one tarball and slurm out messages are ok
            # Prepare a message with information such as
            #   (installation status, tarball name, tarball size)
            comment_update = '\n|%s|finished|:grin: SUCCESS ' % dt.strftime("%b %d %X %Z %Y")
            tarball_size = os.path.getsize(eessi_tarballs[0])/2**30
            comment_update += 'tarball <code>%s</code> (%.3f GiB) ' % (os.path.basename(eessi_tarballs[0]), tarball_size)
            comment_update += 'in job dir|'
            # NOTE explicitly name repo in build job comment?
            # comment_update += '\nAwaiting approval to ingest tarball into the repository.'
        else:
            # something is not allright:
            #  - no slurm out or
            #  - did not find the messages we expect or
            #  - no tarball or
            #  - more than one tarball
            # prepare a message with details about the above conditions and
            # update PR with a comment

            comment_update = '\n|%s|finished|:cry: FAILURE <ul>' % dt.strftime("%b %d %X %Z %Y")
            found_slurm_out = os.path.exists(slurm_out)

            if not found_slurm_out:
                # no slurm out ... something went wrong with the job
                comment_update += '<li>No slurm output <code>%s</code> in job dir</li>' % os.path.basename(slurm_out)
            else:
                comment_update += '<li>Found slurm output <code>%s</code> in job dir</li>' % os.path.basename(slurm_out)

            if found_slurm_out and not no_missing_modules:
                # Found slurm out, but doesn't contain message 'No missing modules!'
                comment_update += '<li>Slurm output lacks message "No missing modules!".</li>'

            if found_slurm_out and not targz_created:
                # Found slurm out, but doesn't contain message
                #   'eessi-.*-software-.*.tar.gz created!'
                comment_update += '<li>Slurm output lacks message about created tarball.</li>'

            if len(eessi_tarballs) == 0:
                # no luck, job just seemed to have failed ...
                comment_update += '<li>No tarball matching <code>%s</code> found in job dir.</li>' % tarball_pattern.replace("*","\*")

            if len(eessi_tarballs) > 1:
                # something's fishy, we only expected a single tar.gz file
                comment_update += '<li>Found %d tarballs in job dir - only 1 matching <code>%s</code> expected.</li>' % (len(eessi_tarballs),tarball_pattern.replace("*","\*"))
            comment_update += '</ul>|'
            #comment_update += '\nAn admin may investigate what went wrong. (TODO implement procedure to ask for details by adding a command to this comment.)'

        # (c) add a row to the table
        # add row to status table if we found a comment
        if 'comment_id' in finished_job:
            issue_comment = pull_request.get_issue_comment(int(finished_job['comment_id']))
            original_body = issue_comment.body
            dt = datetime.now(timezone.utc)
            issue_comment.edit(original_body + comment_update)
        else:
            print("did not obtain/find a comment for the job")
            # TODO just create one?

        # move symlink from job_ids_dir/submitted to jobs_ids_dir/finished
        old_symlink = os.path.join(submitted_jobs_dir, finished_job['jobid'])
        finished_jobs_dir = os.path.join(job_ids_dir,'finished')
        mkdir(finished_jobs_dir)
        new_symlink = os.path.join(finished_jobs_dir, finished_job['jobid'])
        print(f'os.rename({old_symlink},{new_symlink})')
        os.rename(old_symlink, new_symlink)

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

    # before main loop, get list of known jobs (stored on disk)
    # main loop
    #  get current jobs of the bot user (job id, state, reason)
    #    (assume all are jobs building software)
    #  determine new jobs (comparing known and current jobs)
    #    process new jobs (filtered by optional command line option)
    #  determine finished jobs (comparing known and current jobs)
    #    process finished jobs (filtered by optional command line option)
    #  set known jobs to list of current jobs

    max_iter = int(opts.max_manager_iterations)
    # retrieve some settings from app.cfg
    job_ids_dir = ''
    submitted_jobs_dir = ''
    poll_command  = 'false'
    poll_interval = 0
    scontrol_command = ''
    if max_iter != 0:
        job_mgr = config.get_section('job_manager')
        job_ids_dir = job_mgr.get('job_ids_dir')
        submitted_jobs_dir = os.path.join(job_ids_dir,'submitted')
        poll_command = job_mgr.get('poll_command') or false
        poll_interval = int(job_mgr.get('poll_interval') or 0)
        if poll_interval <= 0:
            poll_interval = 60
        scontrol_command = job_mgr.get('scontrol_command') or false
        mkdir(submitted_jobs_dir)

    # who am i
    username = os.getlogin()

    # max_iter
    #   < 0: run loop indefinitely
    #  == 0: don't run loop
    #   > 0: run loop max_iter times
    # processing may be limited to a list of job ids (see parameter -j --jobs)
    i = 0
    if max_iter != 0:
        known_jobs = job_manager.get_known_jobs(submitted_jobs_dir)
    while max_iter < 0 or i < max_iter:
        print("\njob manager main loop: iteration %d" % i)
        print("known_jobs='%s'" % known_jobs)

        current_jobs = job_manager.get_current_jobs(poll_command, username)
        print("current_jobs='%s'" % current_jobs)

        new_jobs = job_manager.determine_new_jobs(known_jobs, current_jobs)
        print("new_jobs='%s'" % new_jobs)
        # process new jobs
        for nj in new_jobs:
            if nj in job_manager.job_filter: 
                job_manager.process_new_job(current_jobs[nj], scontrol_command, submitted_jobs_dir)
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

