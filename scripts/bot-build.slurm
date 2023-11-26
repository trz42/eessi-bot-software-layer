#!/usr/bin/env bash
#
# Slurm job script to call bot/build.sh in target pull request.
#
# This file is part of the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# author: Kenneth Hoste (@boegel)
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#

# ASSUMPTIONs:
#  - working directory has been prepared by the bot with a checkout of a
#    pull request (OR by some other means)
#  - the working directory contains a directory 'cfg' where the main config
#    file 'job.cfg' has been deposited
#  - the directory may contain any additional files references in job.cfg,
#    for example, repos.cfg and configuration file bundles for repositories

echo "Starting bot-build.slurm"
BOT_BUILD_SCRIPT=bot/build.sh
if [ -f ${BOT_BUILD_SCRIPT} ]; then
    echo "${BOT_BUILD_SCRIPT} script found in '${PWD}', so running it!"
    ${BOT_BUILD_SCRIPT}
else
    echo "could not find ${BOT_BUILD_SCRIPT} script in '${PWD}'" >&2
    exit 1
fi
echo "bot/build.sh finished"
CHECK_BUILD_SCRIPT=bot/check-build.sh
if [ -f ${CHECK_BUILD_SCRIPT} ]; then
    echo "${CHECK_BUILD_SCRIPT} script found in '${PWD}', so running it!"
    ${CHECK_BUILD_SCRIPT}
else
    echo "could not find ${CHECK_BUILD_SCRIPT} script in '${PWD}' ..."
    echo "... depositing default _bot_job${SLURM_JOB_ID}.result file in '${PWD}'"
    cat << 'EOF' > _bot_job${SLURM_JOB_ID}.result
[RESULT]
comment_description = <details><summary>:shrug: UNKNOWN _(click triangle for detailed information)_<summary/><ul><li>Did not find `bot/check-result.sh` script in job's work directory.</li><li>*Check job manually or ask an admin of the bot instance to assist you.*</li></ul></details>
status = UNKNOWN
artefacts =
EOF
fi
echo "check build step finished"
TEST_SCRIPT=bot/test.sh
if [ -f ${TEST_SCRIPT} ]; then
    echo "${TEST_SCRIPT} script found in '${PWD}', so running it!"
    ${TEST_SCRIPT}
    echo "${TEST_SCRIPT} finished"
else
    echo "could not find ${TEST_SCRIPT} script in '${PWD}'" >&2
fi
CHECK_TEST_SCRIPT=bot/check-test.sh
if [ -f ${CHECK_TEST_SCRIPT} ]; then
    echo "${CHECK_TEST_SCRIPT} script found in '${PWD}', so running it!"
    ${CHECK_TEST_SCRIPT}
else
    echo "could not find ${CHECK_TEST_SCRIPT} script in '${PWD}' ..."
    echo "... depositing default _bot_job${SLURM_JOB_ID}.test file in '${PWD}'"
    cat << 'EOF' > _bot_job${SLURM_JOB_ID}.test
[RESULT]
comment_description = <details><summary>:shrug: UNKNOWN _(click triangle for detailed information)_<summary/><ul><li>Did not find `bot/check-test.sh` script in job's work directory.</li><li>*Check job manually or ask an admin of the bot instance to assist you.*</li></ul></details>
status = UNKNOWN
artefacts =
EOF
fi
echo "check test step finished"
