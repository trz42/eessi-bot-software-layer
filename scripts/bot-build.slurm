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
if [ -f bot/build.sh ]; then
    echo "bot/build.sh script found in '${PWD}', so running it!"
    bot/build.sh
else
    fatal_error "could not find bot/build.sh script in '${PWD}'"
fi
echo "bot/build.sh finished"
if [ -f bot/check-result.sh ]; then
    echo "bot/check-result.sh script found in '${PWD}', so running it!"
    bot/check-result.sh
else
    echo "could not find bot/check-result.sh script in '${PWD}' ..."
    echo "... depositing default _bot_job${SLURM_JOB_ID}.result file in '${PWD}'"
    cat > _bot_job${SLURM_JOB_ID}.result <<EOF
result=UNKNOWN
msg="Did not find bot/check-result.sh script in '${PWD}'. Check job manually."
EOF
fi
echo "check result step finished"
