# This file is part of the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# author: Bob Droege (@bedroge)
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#
import datetime

from tools import config
from github import Github, GithubIntegration

_token = None
_gh = None

def get_token():
    global _token
    app_id = config.get_section('github').get('app_id')
    installation_id = config.get_section('github').get('installation_id')
    private_key_path = config.get_section('github').get('private_key')
    private_key = ''

    with open(private_key_path, 'r') as private_key_file:
        private_key = private_key_file.read()

    github_integration = GithubIntegration(app_id, private_key)
    # Note that installation access tokens last only for 1 hour, you will need to regenerate them after they expire.
    _token = github_integration.get_access_token(installation_id)

    return _token


def connect():
    return Github(get_token().token)


def get_instance():
    global _gh, _token
    if not _gh or (_token and datetime.datetime.utcnow() > _token.expires_at):
        _gh = connect()
    return _gh

def token():
    global _token
    return _token
