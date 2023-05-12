#!/usr/bin/env python3
#
# This file is part of the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# author: Kenneth Hoste (@boegel)
# author: Bob Droege (@bedroge)
# author: Hafsa Naeem (@hafsa-naeem)
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#
import waitress
import sys
import tasks.build as build
import tasks.deploy as deploy

from connections import github
from tools import config
from tools.args import event_handler_parse
from tools.commands import get_bot_command, EESSIBotCommand, EESSIBotCommandError
from tools.filter import EESSIBotActionFilter
from tools.permissions import check_command_permission
from tools.pr_comments import update_pr_comment
from tasks.build import check_build_permission, submit_build_jobs, get_repo_cfg, get_architecturetargets
from tasks.deploy import deploy_built_artefacts

from pyghee.lib import PyGHee, create_app, get_event_info, read_event_from_json
from pyghee.utils import log


GITHUB = "github"
APP_NAME = "app_name"
REPO_TARGET_MAP = "repo_target_map"


class EESSIBotSoftwareLayer(PyGHee):

    def __init__(self, *args, **kwargs):
        """
        EESSIBotSoftwareLayer constructor.
        """
        super(EESSIBotSoftwareLayer, self).__init__(*args, **kwargs)

        self.cfg = config.read_config()
        event_handler_cfg = self.cfg['event_handler']
        self.logfile = event_handler_cfg.get('log_path')

    def log(self, msg, *args):
        """
        Logs a message incl the caller's function name by passing msg and *args to PyGHee's log method.

        Args:
            msg (string): message (format) to log to event handler log
            *args (any): any values to be substituted into msg
        """
        funcname = sys._getframe().f_back.f_code.co_name
        if args:
            msg = msg % args
        msg = "[%s]: %s" % (funcname, msg)
        log(msg, log_file=self.logfile)

    def handle_issue_comment_event(self, event_info, log_file=None):
        """
        Handle adding/removing of comment in issue or PR.
        """
        request_body = event_info['raw_request_body']
        issue_url = request_body['issue']['url']
        action = request_body['action']
        sender = request_body['sender']['login']
        owner = request_body['comment']['user']['login']
        # next two lines are commented out and replaced to write less to log files
        # txt = request_body['comment']['body']
        # self.log(f"Comment in {issue_url} (owned by @{owner}) {action} by @{sender}: {txt}")
        self.log(f"Comment in {issue_url} (owned by @{owner}) {action} by @{sender}")

        # check if addition to comment includes a command for the bot, e.g.,
        #   bot: build [arch:intel] [instance:AWS]
        #   bot: cancel [job:jobid]
        #   bot: disable [arch:generic]
        # actions: created, edited
        # created -> comment.body
        # edited -> comment.body - changes.body.from
        # procedure:
        #  - determine what's new (assume new is at the end)
        #  - scan what's new for commands 'bot: COMMAND [ARGS*]'
        #  - process commands

        # first check if sender is authorized to send any command
        # - double purpose:
        #   1. check permission
        #   2. skip any comment updates that were done by the bot itself --> we
        #      prevent the bot entering an endless loop where it reacts on
        #      updates to comments it made itself
        #      NOTE this assumes that the sender of the event is corresponding to
        #      the bot if the bot updates comments itself and that the bot is not
        #      given permission in the configuration setting 'command_permission'
        #      ... in order to prevent surprises we should be careful what the bot
        #      adds to comments, for example, before updating a comment it could
        #      run the update through the function checking for a bot command.
        if check_command_permission(sender) is False:
            self.log(f"account `{sender}` has NO permission to send commands to bot")
            return
        else:
            self.log(f"account `{sender}` has permission to send commands to bot")

        # only scan for comments in newly created comments
        if action == 'created':
            comment_new = request_body['comment']['body']
            # next line commented out and replaced to write less to log files
            # self.log(f"comment created:\n########\n{comment_new.rstrip()}\n########")
            self.log(f"comment action '{action}' is handled")
        else:
            self.log(f"comment action '{action}' not handled")
            return

        # search for commands in what is new in comment
        # init comment_update with an empty string or later split would fail if
        # it is None
        comment_update = ''
        commands = []
        for line in comment_new.split('\n'):
            # next line commented out to write less to log files
            # self.log(f"searching line '{line}' for bot command")
            line_stripped = line.strip()
            if line.isspace() or len(line_stripped) == 0:
                # next line commented out to write less to log files
                # self.log(f"line '{line}' is empty")
                continue
            bot_command = get_bot_command(line)
            if bot_command:
                try:
                    ebc = EESSIBotCommand(bot_command)
                except EESSIBotCommandError as bce:
                    self.log(f"ERROR: parsing bot command '{bot_command}' failed with {bce.args}")
                    # next two lines commented out to make the bot less noisy,
                    # could be enabled again if bot commands accept arg --verbose
                    # or bot instance has a similar setting
                    # comment_update += f"\n- parsing bot command `{bot_command}` received"
                    # comment_update += f" from sender `{sender}` failed"
                    continue
                commands.append(ebc)
                self.log(f"found bot command: '{bot_command}'")
                comment_update += "\n- received bot command "
                comment_update += f"`{bot_command}`"
                comment_update += f" from `{sender}` (expanded command format: `{ebc.to_string()}`)"
            # next two lines are commented out to write less to log files
            # else:
                # self.log(f"'{line}' is not considered to contain a bot command")
                # next three lines commented out to make the bot less noisy,
                # could be enabled again if bot commands accept arg --verbose
                # or bot instance has a similar setting
                # comment_update += f"\n- line <code>{line}</code> is not considered to contain a bot command"
                # comment_update += "\n- bot commands begin with `bot: `, make sure"
                # comment_update += "\n  there is no whitespace at the beginning of a line"

        if comment_update == '':
            # no update to be added, just log and return
            self.log("update to comment is empty")
            return
        else:
            self.log(f"comment update: '{comment_update}'")

        if not any(map(get_bot_command, comment_update.split('\n'))):
            # the 'not any()' ensures that the update would not be considered a bot command itself
            # ... together with checking the sender of a comment update this aims
            # at preventing the bot to enter an endless loop in commenting on its own
            # comments
            update_pr_comment(event_info, comment_update)
        else:
            self.log(f"update '{comment_update}' is considered to contain bot command ... not updating PR comment")

        # process commands
        for cmd in commands:
            try:
                update = self.handle_bot_command(event_info, cmd)
                # the update to the PR comment is only done if the command is
                # 'help'; otherwise there was too much noise and also updates
                # were a bit confusing when different instances overwrote
                # comments of the other instances
                if cmd.command == 'help':
                    comment_update += f"\n- handling `{cmd.command}` resulted in: "
                    comment_update += update
                    update_pr_comment(event_info, comment_update)

                self.log(f"handling '{cmd.command}' resulted in '{update}'")

            except EESSIBotCommandError as bce:
                self.log(f"ERROR: handling {cmd.command} failed with {bce.args}")
                # next two lines commented out to make the bot less noisy,
                # could be enabled again if bot commands accept arg --verbose
                # or bot instance has a similar setting
                # comment_update += f"\n- handling `{cmd.command}` failed with {bce.args}"
                # update_pr_comment(event_info, comment_update)
                continue
            except Exception as err:
                log(f"Unexpected err={err}, type(err)={type(err)}")
                raise

        self.log("issue_comment event handled!")

    def handle_installation_event(self, event_info, log_file=None):
        """
        Handle installation of app.
        """
        request_body = event_info['raw_request_body']
        user = request_body['sender']['login']
        action = request_body['action']
        # repo_name = request_body['repositories'][0]['full_name'] # not every action has that attribute
        self.log("App installation event by user %s with action '%s'", user, action)
        self.log("installation event handled!")

    def handle_pull_request_labeled_event(self, event_info, pr):
        """
        Handle adding of a label to a pull request.
        """

        # determine label
        label = event_info['raw_request_body']['label']['name']
        self.log("Process PR labeled event: PR#%s, label '%s'", pr.number, label)

        if label == "bot:build":
            # run function to build software stack
            if check_build_permission(pr, event_info):
                # use an empty filter
                submit_build_jobs(pr, event_info, EESSIBotActionFilter(""))

        elif label == "bot:deploy":
            # run function to deploy built artefacts
            deploy_built_artefacts(pr, event_info)
        else:
            self.log("handle_pull_request_labeled_event: no handler for label '%s'", label)

    def handle_pull_request_opened_event(self, event_info, pr):
        """
        Handle opening of a pull request.
        """
        self.log("PR opened: waiting for label bot:build")
        app_name = self.cfg[GITHUB][APP_NAME]
        # TODO check if PR already has a comment with arch targets and
        # repositories
        arch_map = get_architecturetargets(self.cfg)
        repo_cfg = get_repo_cfg(self.cfg)

        comment = f"Instance `{app_name}` is configured to build:"

        for arch in arch_map.keys():
            # check if repo_target_map contains an entry for {arch}
            if arch not in repo_cfg[REPO_TARGET_MAP]:
                self.log(f"skipping arch {arch} because repo target map does not define repositories to build for")
                continue
            for repo_id in repo_cfg[REPO_TARGET_MAP][arch]:
                comment += f"\n- arch `{'/'.join(arch.split('/')[1:])}` for repo `{repo_id}`"

        self.log(f"PR opened: comment '{comment}'")

        # create comment to pull request
        repo_name = pr.base.repo.full_name
        gh = github.get_instance()
        repo = gh.get_repo(repo_name)
        pull_request = repo.get_pull(pr.number)
        issue_comment = pull_request.create_issue_comment(comment)
        return issue_comment

    def handle_pull_request_event(self, event_info, log_file=None):
        """
        Handle 'pull_request' event
        """
        action = event_info['action']
        gh = github.get_instance()
        self.log("repository: '%s'", event_info['raw_request_body']['repository']['full_name'])
        pr = gh.get_repo(event_info['raw_request_body']['repository']
                         ['full_name']).get_pull(event_info['raw_request_body']['pull_request']['number'])
        self.log("PR data: %s", pr)

        handler_name = 'handle_pull_request_%s_event' % action
        if hasattr(self, handler_name):
            handler = getattr(self, handler_name)
            self.log("Handling PR action '%s' for PR #%d...", action, pr.number)
            handler(event_info, pr)
        else:
            self.log("No handler for PR action '%s'", action)

    def handle_bot_command(self, event_info, bot_command, log_file=None):
        """
        Handle bot command

        Args:
            event_info (dict): object containing all information of the event
            bot_command (EESSIBotCommand): command to be handled
        """
        cmd = bot_command.command
        handler_name = f"handle_bot_command_{cmd}"
        if hasattr(self, handler_name):
            handler = getattr(self, handler_name)
            self.log(f"Handling bot command {cmd}")
            return handler(event_info, bot_command)
        else:
            self.log(f"No handler for command '{cmd}'")
            raise EESSIBotCommandError(f"unknown command '{cmd}'; use `bot: help` for usage information")

    def handle_bot_command_help(self, event_info, bot_command):
        help_msg = "\n  **How to send commands to bot instances**"
        help_msg += "\n  - Commands must be sent with a **new** comment (edits of existing comments are ignored)."
        help_msg += "\n  - A comment may contain multiple commands, one per line."
        help_msg += "\n  - Every command begins at the start of a line and has the syntax `bot: COMMAND [ARGUMENTS]*`"
        help_msg += "\n  - Currently supported COMMANDs are: `help`, `build`, `showconfig`"
        return help_msg

    def handle_bot_command_build(self, event_info, bot_command):
        gh = github.get_instance()
        self.log("repository: '%s'", event_info['raw_request_body']['repository']['full_name'])
        repo_name = event_info['raw_request_body']['repository']['full_name']
        pr_number = event_info['raw_request_body']['issue']['number']
        pr = gh.get_repo(repo_name).get_pull(pr_number)
        build_msg = ''
        if check_build_permission(pr, event_info):
            # use filter from command
            build_msg = submit_build_jobs(pr, event_info, bot_command.action_filters)
        else:
            request_body = event_info['raw_request_body']
            sender = request_body['sender']['login']
            build_msg = f"account {sender} has no permission to submit build jobs"
        return build_msg

#    def handle_bot_command_deploy(self, event_info, bot_command):
#        return

#    def handle_bot_command_enable(self, event_info, bot_command):
#        return

#    def handle_bot_command_disable(self, event_info, bot_command):
#        return

#    def handle_bot_command_cancel(self, event_info, bot_command):
#        return

#    def handle_bot_command_status(self, event_info, bot_command):
#        return

    def handle_bot_command_showconfig(self, event_info, bot_command):
        self.log("processing bot command 'showconfig'")
        gh = github.get_instance()
        repo_name = event_info['raw_request_body']['repository']['full_name']
        pr_number = event_info['raw_request_body']['issue']['number']
        pr = gh.get_repo(repo_name).get_pull(pr_number)
        issue_comment = self.handle_pull_request_opened_event(event_info, pr)
        return f"added comment {issue_comment.issue_url} to show configuration"

    def start(self, app, port=3000):
        """starts the app and log information in the log file

        Args:
            app (object): instance of class EESSIBotSoftwareLayer
            port (int, optional): Defaults to 3000.
        """
        start_msg = "EESSI bot for software layer started!"
        print(start_msg)
        self.log(start_msg)
        port_info = "app is listening on port %s" % port
        print(port_info)
        self.log(port_info)

        event_handler_cfg = self.cfg['event_handler']
        my_logfile = event_handler_cfg.get('log_path')
        log_file_info = "logging in to %s" % my_logfile
        print(log_file_info)
        self.log(log_file_info)
        waitress.serve(app, listen='*:%s' % port)


def main():
    """Main function."""
    opts = event_handler_parse()

    required_config = {
        build.SUBMITTED_JOB_COMMENTS: [build.INITIAL_COMMENT, build.AWAITS_RELEASE],
        build.BUILDENV: [build.NO_BUILD_PERMISSION_COMMENT],
        deploy.DEPLOYCFG: [deploy.NO_DEPLOY_PERMISSION_COMMENT]
    }
    # config is read and checked for settings to raise an exception early when the event_handler starts.
    config.check_required_cfg_settings(required_config)
    github.connect()

    if opts.file:
        app = create_app(klass=EESSIBotSoftwareLayer)
        event = read_event_from_json(opts.file)
        event_info = get_event_info(event)
        app.handle_event(event_info)
    elif opts.cron:
        app.log("Running in cron mode")
    else:
        # Run as web app
        app = create_app(klass=EESSIBotSoftwareLayer)
        app.start(app, port=opts.port)


if __name__ == '__main__':
    main()
