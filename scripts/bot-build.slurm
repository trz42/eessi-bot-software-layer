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
    echo "could not find bot/build.sh script in '${PWD}'" >&2
    exit 1
fi
