# This file is part of the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#

# Standard library imports
# (none yet)

# Third party imports (anything installed into the local Python environment)
# (none yet)

# Local application imports (anything from EESSI/eessi-bot-software-layer)
# (none yet)


# access to a CernVM-FS repository is defined via a repos.cfg file and associated
# tarballs containing configuration settings per repository
# below, we define constants for the settings of each repository;
# the section name, eg, 'eessi-2023.06' in '[eessi-2023.06]' is not fixed and
# therefore no constant is defined for itsections and 'settings' in these files
#
# cfg/repos.cfg
REPOS_CFG_CONFIG_BUNDLE = "config_bundle"
REPOS_CFG_CONFIG_MAP = "config_map"
REPOS_CFG_CONTAINER = "container"
REPOS_CFG_REPO_NAME = "repo_name"
REPOS_CFG_REPO_VERSION = "repo_version"
