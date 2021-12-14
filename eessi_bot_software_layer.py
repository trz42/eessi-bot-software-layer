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

LOG = os.path.join(os.getenv('HOME'), 'eessi-bot-software-layer.log')


def log(msg):
    """
    Log message
    """
    with open(LOG, 'a') as fh:
        timestamp = datetime.datetime.now().strftime("%Y%m%d-T%H:%M:%S")
        fh.write('[' + timestamp + '] ' + msg + '\n')


def log_event(request):
    """
    Log event data
    """
    event_type = request.headers['X-GitHub-Event']
    msg_txt = '\n'.join([
        "Event type: %s" % event_type,
        #"Request headers: %s" % pprint.pformat(dict(request.headers)),
        #"Request body: %s" % pprint.pformat(request.json),
        "Event data (JSON): %s" % json.dumps({'headers': dict(request.headers), 'json': request.json}, indent=4),
        '',
    ])
    log(msg_txt)


def read_event_from_json(jsonfile):
    """
    Read in event data from a json file.
    """
    req = namedtuple('Request', ['headers', 'json'])
    with open(jsonfile, 'r') as jf:
        event_data = json.load(jf)
        req.headers = CaseInsensitiveDict(event_data['headers'])
        req.json = event_data['json']
    return req


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
    return create_app(gh)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        event = read_event_from_json(sys.argv[1])
        log_event(event)
    else:
        app = main()
        app.run()
