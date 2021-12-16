import os

from github import Github

def connect_to_github():
    return Github(os.getenv('GITHUB_TOKEN'))
