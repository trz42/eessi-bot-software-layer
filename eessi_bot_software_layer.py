#!/usr/bin/env python3
#
# GitHub App for the EESSI project
#
# A bot to help with requests to add software installations to the EESSI software layer,
# see https://github.com/EESSI/software-layer
#
# author: Kenneth Hoste (@boegel)
#
# license: GPLv2
#

import waitress
import json

from connections import github
from tools import args, config
from tasks.build import build_easystack_from_pr

from pyghee.lib import PyGHee, create_app, read_event_from_json
from pyghee.utils import log

class EESSIBotSoftwareLayer(PyGHee):
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


    def handle_pr_label_event(self, event_info, pr):
        """
        Handle adding of a label to a pull request.
        """
        log("PR labeled")


    def handle_pr_opened_event(self, event_info, pr):
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
        log("PR action: %s" % action)
        gh = github.get_instance()
#        log("raw_request_body: '%s'" % event_info['raw_request_body'])
#        log("repository: '%s'" % json.dumps(event_info['raw_request_body']['repository'],indent=4,sort_keys=True) )
        log("repository: '%s'" % event_info['raw_request_body']['repository']['full_name'] )
        pr = gh.get_repo(event_info['raw_request_body']['repository']['full_name']).get_pull(event_info['raw_request_body']['pull_request']['number'])
        log("PR data: %s" % pr)

        handlers = {
            'labeled': self.handle_pr_label_event,
            'opened': self.handle_pr_opened_event,
        #    'closed': handle_pr_opened_event,
        #    'unlabeled': handle_pr_label_event,
        }
        handler = handlers.get(action)
        if handler:
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
        waitress.serve(app, listen='*:3000')

if __name__ == '__main__':
    main()

