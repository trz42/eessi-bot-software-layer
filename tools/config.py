# This file is part of the EESSI build-and-deploy bot,
# see https://github.com/EESSI/eessi-bot-software-layer
#
# The bot helps with requests to add software installations to the
# EESSI software layer, see https://github.com/EESSI/software-layer
#
# author: Bob Droege (@bedroge)
#
# license: GPLv2
#
import configparser
import json
import sys

from .logging import log, error

_config = {}

# defined configuration sections
SECTION_GITHUB = "github"
SECTION_BUILDENV = "buildenv"
SECTION_DEPLOYCFG = "deploycfg"
SECTION_ARCHITECTURETARGETS = "architecturetargets"
SECTION_JOB_MANAGER = "job_manager"

# defined configuration options
OPTION_APP_ID = "app_id"
OPTION_APP_NAME = "app_name"
OPTION_INSTALLATION_ID = "installation_id"
OPTION_PRIVATE_KEY = "private_key"
OPTION_BUILD_JOB_SCRIPT = "build_job_script"
OPTION_CVMFS_CUSTOMIZATIONS = "cvmfs_customizations"
OPTION_HTTP_PROXY = "http_proxy"
OPTION_HTTPS_PROXY = "https_proxy"
OPTION_JOBS_BASE_DIR = "jobs_base_dir"
OPTION_LOAD_MODULES = "load_modules"
OPTION_LOCAL_TMP = "local_tmp"
OPTION_SLURM_PARAMS = "slurm_params"
OPTION_SUBMIT_COMMAND = "submit_command"
OPTION_UPLOAD_TO_S3_SCRIPT = "upload_to_s3_script"
OPTION_ENDPOINT_URL = "endpoint_url"
OPTION_BUCKET_NAME = "bucket_name"
OPTION_UPLOAD_POLICY = "upload_policy"
OPTION_DEPLOY_PERMISSION = "deploy_permission"
OPTION_ARCH_TARGET_MAP = "arch_target_map"
OPTION_JOB_IDS_DIR = "job_ids_dir"
OPTION_POLL_COMMAND = "poll_command"
OPTION_POLL_INTERVAL = "poll_interval"
OPTION_SCONTROL_COMMAND = "scontrol_command"


def read_file(path):
    """
    Read a given configuration file.

    Args:
        path (string): path to configuration file
    """
    global _config
    _config = configparser.ConfigParser()
    try:
        _config.read(path)
    except Exception as e:
        print(e)
        error(f'Unable to read configuration file {path}!')


def read_and_validate_config(path, required_config, log_file=None):
    """Reads the configuration file and validates that all required sections
       and options are defined.

    Args:
        path (string): path to the configuration file
        required_config (dict): dictionary holding required {section, options}
        log_file (fh): logging output to

    Returns:
        dict (str, dict): dictionary containing configuration settings
    """
    fn = sys._getframe().f_code.co_name

    config = configparser.ConfigParser()
    try:
        config.read(path)
    except Exception:
        error(f"{fn}(): Unable to read configuration file {path}!")

    # Check if all required configuration sections and options can be found.
    # Also, process some values that are not just strings.
    for section in required_config.keys():
        if section not in config:
            error(f"{fn}(): Missing section '{section}' in config file {path}.")
        for item in required_config[section]:
            if item not in config[section]:
                error(f"{fn}(): Missing item '{item}' in section '[{section}]' "
                      f"in config file {path}")
            log(f"{fn}(): added {section}[{item}] = {config[section][item]}", log_file=log_file)

    return config


def convert_cvmfs_customizations_option(option, log_file=None):
    """Convert CVMFS_CUSTOMIZATIONS option to json dictionary.

    Args:
        option (string): value for app.cfg option CVMFS_CUSTOMIZATIONS
        log_file (fh): logging output to

    Returns:
        cvmfs_customizations (dict): dictionary containing the customizations
    """
    fn = sys._getframe().f_code.co_name

#        cvmfs_customizations_str = config[section].get(OPTION_CVMFS_CUSTOMIZATIONS)
    cvmfs_customizations = {}
    try:
        log(f"{fn}(): cvmfs_customizations_str '{option}'", log_file=log_file)

        if option is not None:
            cvmfs_customizations = json.loads(option)

        log(f"{fn}(): cvmfs_customizations '{json.dumps(cvmfs_customizations)}'", log_file=log_file)
    except json.decoder.JSONDecodeError as e:
        print(e)
        error(f"{fn}(): value for option 'cvmfs_customizations' "
              f"({option}) could not be decoded.")

    return cvmfs_customizations


def get_section(name):
    if name in _config:
        return _config[name]
    else:
        return {}
