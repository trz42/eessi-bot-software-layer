import flask
import os

from connections import github
from tasks.build import build_easystack_from_pr
from tools.logging import log

def handle_pr_label_event(request, pr):
    """
    Handle adding of a label to a pull request.
    """
    log("PR labeled")


def handle_pr_opened_event(request, pr):
    """
    Handle opening of a pull request.
    """
    log("PR opened")
    build_easystack_from_pr(pr, request)


def handle_pr_event(request):
    """
    Handle 'pull_request' event
    """
    action = request.json['action']
    log("PR action: %s" % action)
    gh = github.get_instance()
    pr = gh.get_repo(request.json['repository']['full_name']).get_pull(request.json['pull_request']['number'])
    log("PR data: %s" % pr)

    handlers = {
        'labeled': handle_pr_label_event,
        'opened': handle_pr_opened_event,
    #    'closed': handle_pr_opened_event,
    #    'unlabeled': handle_pr_label_event,
    }
    handler = handlers.get(action)
    if handler:
        log("Handling PR action '%s' for PR #%d..." % (action, pr.number))
        handler(request, pr)
    else:
        log("No handler for PR action '%s'" % action)

    return flask.Response(status=200)
