#!/usr/bin/env bash
#
# GitHub App for the EESSI project: slurm batch script
#
# A bot to help with requests to add software installations to the EESSI software layer,
# see https://github.com/EESSI/software-layer
#
# author: Kenneth Hoste (@boegel)
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#
#
#SBATCH --time 24:00:00
#SBATCH --nodes 1
#SBATCH --exclusive
# make job script unworkable by default ... requires '--constraint ...' on command line
#SBATCH --constraint shape=unknown

# ASSUMPTIONs:
#  - running from a job environment on shared disc
#  - the job environment contains a checkout of the branch of the pull
#    request
#  - arguments: 
#    - eessi_tmpdir: hand over as argument to script

if [ $# -ne 1 ]; then
    echo "ERROR: Usage: $0 <EESSI tmp dir (example: /tmp/$USER/EESSI)>" >&2
    exit 1
fi
eessi_tmpdir=$1

# map the current directory (job environment which contains checkout
#   of the branch of the pull request) to a specific path inside the container
#export SINGULARITY_BIND="$(pwd):/eessi_bot_job"

# run standard EESSI software-layer build script via compat layer
#   inside build container
export SINGULARITY_HOME="$(pwd):/eessi_bot_job"
./build_container.sh run ${eessi_tmpdir} ./install_software_layer.sh

# create tarball for the above build and place it in some specific
#   directory on shared disc (just in main directory of job)
#   see https://github.com/EESSI/eessi-bot-software-layer/issues/7
EESSI_SILENT=1 source init/eessi_environment_variables
software_subdir=$(echo ${EESSI_SOFTWARE_SUBDIR} | tr '/' '-')
timestamp=$(date +%s)
export TGZ=$(printf "eessi-%s-software-%s-%s-%d.tar.gz" ${EESSI_PILOT_VERSION} ${EESSI_OS_TYPE} ${software_subdir} ${timestamp})
./build_container.sh run ${eessi_tmpdir} \
    ./create_tarball.sh ${eessi_tmpdir} ${EESSI_PILOT_VERSION} \
    ${EESSI_SOFTWARE_SUBDIR} /eessi_bot_job/${TGZ}
