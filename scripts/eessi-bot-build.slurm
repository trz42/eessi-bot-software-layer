#!/usr/bin/env bash
#
# Slurm job script to install additional software into EESSI via build container
#
# This is part of the GitHub App for the EESSI project:
# A bot to help with requests to add software installations to the EESSI software layer,
# see https://github.com/EESSI/software-layer
#
# author: Kenneth Hoste (@boegel)
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#
#

# ASSUMPTIONs:
#  - running from a job environment on shared disc
#  - the job environment contains a checkout of the branch of the pull
#    request
#  - arguments: 
#    - eessi_tmpdir: hand over as argument to script

if [ $# -lt 1 ]; then
    echo "ERROR: Usage: $0 <EESSI tmp dir (example: /tmp/$USER/EESSI)> <any additional options (example: --generic)>" >&2
    exit 1
fi
eessi_tmpdir=$1
shift

echo "Starting eessi-bot-build-slurm.sh"

echo -n "updating \$eessi_tmpdir: '$eessi_tmpdir' -> "
# replace any env variable in $eessi_tmpdir with its
#   current value (e.g., a value that is local to the job)
eessi_tmpdir=$(envsubst <<< $eessi_tmpdir)
echo "'$eessi_tmpdir'"

# bind current working directory to /eessi_bot_job in build container,
# and also use it as home directory in build container
export SINGULARITY_HOME="$(pwd):/eessi_bot_job"

# if eessi_tmpdir is not starting with '/tmp' map it to '/tmp'
# rationale: something else than /tmp is used for eessi_tmpdir
#            if /tmp has some limitations (e.g., size);
#            the bot job is then provided with a (job-specific)
#            alternative via the bot's config key local_tmp;
#            because many downstream scripts assume temporary
#            storage under /tmp, the alternative is mapped to
#            /tmp inside the container;
#            the mapping is only needed if $eessi_tmpdir not
#            already points to /tmp
if [[ $eessi_tmpdir != /tmp* ]] ;
then
    export SINGULARITY_BIND="$eessi_tmpdir:/tmp"
fi

echo "SINGULARITY_BIND=${SINGULARITY_BIND}"

# run standard EESSI software-layer install script
#   in compat layer environment inside build container
./build_container.sh run ${eessi_tmpdir} ./install_software_layer.sh "$@"

# create tarball for the above build and place it in some specific
#   directory on shared disk (just in main directory of job)
#   see https://github.com/EESSI/eessi-bot-software-layer/issues/7
#pwd
#ls -lisa init/eessi_environment_variables
# the next line only works as intended if the intended repo is mounted on the host
#   when building for a repo that is only available via the container and a
#   custom setup, it is not working
#EESSI_SILENT=0 source init/eessi_environment_variables
#echo "eessi-bot-build.slurm: EESSI_SOFTWARE_SUBDIR=${EESSI_SOFTWARE_SUBDIR}="
#software_subdir=$(echo ${EESSI_SOFTWARE_SUBDIR} | tr '/' '-')
#echo "eessi-bot-build.slurm: software_subdir=${software_subdir}="
#timestamp=$(date +%s)
#export TGZ=$(printf "eessi-%s-software-%s-%s-%d.tar.gz" ${EESSI_PILOT_VERSION} ${EESSI_OS_TYPE} ${software_subdir} ${timestamp})
./build_container.sh run ${eessi_tmpdir} \
    ./create_tarball.sh ${eessi_tmpdir} software /eessi_bot_job "$@"
#    ${EESSI_SOFTWARE_SUBDIR} /eessi_bot_job/${TGZ}
