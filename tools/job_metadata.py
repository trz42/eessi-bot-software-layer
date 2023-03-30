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


def read_job_metadata_from_file(filepath, log_file=None):
    """
    Check if metadata file exists, read it and return 'PR' section if so, return None if not.

    Args:
        filepath (string): path to job metadata file
        log_file (string): path to job metadata file

    Returns:
        job_metadata (dict): dictionary containing job metadata or None
    """

    # check if metadata file exist
    if os.path.isfile(filepath):
        log(f"Found metadata file at {filepath}", log_file)
        metadata = configparser.ConfigParser()
        try:
            metadata.read(filepath)
        except Exception as err:
            error(f"Unable to read job metadata file {filepath}: {err}")

        # get PR section
        if "PR" in metadata:
            metadata_pr = metadata["PR"]
        else:
            metadata_pr = {}
        return metadata_pr
    else:
        log(f"No metadata file found at {filepath}, might not be a bot job", log_file)
        return None

