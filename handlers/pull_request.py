import flask

from tools.logging import log

def handle_pr_label_event(gh, request, pr):
    """
    Handle adding of a label to a pull request.
    """
    log("PR labeled")


def handle_pr_opened_event(gh, request, pr):
    """
    Handle opening of a pull request.
    """
    log("PR opened")


def handle_pr_event(gh, request):
    """
    Handle 'pull_request' event
    """
    action = request.json['action']
    log("PR action: %s" % action)
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
        handler(gh, request, pr)
    else:
        log("No handler for PR action '%s'" % action)

    return flask.Response(status=200)
