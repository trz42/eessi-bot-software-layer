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
import datetime
import flask
import github
import json
import os
import pprint
import sys
from collections import namedtuple
from requests.structures import CaseInsensitiveDict

import handlers
from tools.logging import log, log_event


def read_event_from_json(jsonfile):
    """
    Read event data from a json file.
    """
    req = namedtuple('Request', ['headers', 'json'])
    with open(jsonfile, 'r') as jf:
        event_data = json.load(jf)
        req.headers = CaseInsensitiveDict(event_data['headers'])
        req.json = event_data['json']
    return req


def handle_event(gh, request):
    """
    Handle event
    """
    event_type = request.headers["X-GitHub-Event"]

    event_handler = handlers.event_handlers.get(event_type)
    if event_handler:
        event_handler(gh, request)
    else:
        log("Unsupported event type: %s" % event_type)
        response_data = {'Unsupported event type': event_type}
        response_object = json.dumps(response_data, default=lambda obj: obj.__dict__)
        return flask.Response(response_object, status=400, mimetype='application/json')


def create_app(gh):
    """
    Create Flask app.
    """

    app = flask.Flask(__name__)

    @app.route('/', methods=['POST'])
    def main():
        # verify_request(flask.request)
        log_event(flask.request)
        # handle_event(gh, flask.request)
        return ''

    return app


def main():
    """Main function."""

    gh = github.Github(os.getenv('GITHUB_TOKEN'))
    if len(sys.argv) > 1:
        event = read_event_from_json(sys.argv[1])
        log_event(event)
        handle_event(gh, event)
    else:
        app = create_app(gh)
        app.run()


if __name__ == '__main__':
    main()

