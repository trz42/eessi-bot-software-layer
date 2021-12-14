from .pull_request import handle_pr_event

event_handlers = {
    'pull_request': handle_pr_event,
}
