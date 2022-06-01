#!/usr/bin/env bash

#SBATCH --time 01:00:00
#SBATCH --nodes 1
#SBATCH --exclusive
# make job script unworkable by default ... requires '--constraint ...' on command line
#SBATCH --constraint shape=unknown

# assumes script is started in directory containing softwarelist.yaml (env var SOFTWARE_FILE contains name of file)
# also needs
#   directory where common and site specific scripts are stored (env var SCRIPTS_DIR)
#   NOT USED ANYMORE job directory (env var JOB_DIR == current directory?)
#   space for temporary data (env var LOCAL_TMP)
#   not really needed for this script as long as the info (OS, ARCH) can be generated on the host via archspec
#     target architecture (env var BUILD_TARGET_ARCHITECTURE); the info is later derived and stored in variables
#     EESSI_OS_TYPE and EESSI_SOFTWARE_SUBDIR
#   EESSI version (env var BUILD_EESSI_VERSION)

if [ ! -e ${SOFTWARE_FILE} ]; then
    echo "software file '${SOFTWARE_FILE}' does not exist in current directory; check logs of bot"
    exit 1
fi

if [ x"${SCRIPTS_DIR}" == "x" ]; then
    echo "variable SCRIPTS_DIR is not set; provide it via 'app.cfg'"
    exit 2
fi

# export JOB_DIR=$(pwd)

if [ x"${LOCAL_TMP}" == "x" ]; then
    echo "variable LOCAL_TMP is not set; provide it via 'app.cfg'"
    exit 3
fi

if [ x"${BUILD_TARGET_ARCHITECTURE}" == "x" ]; then
    echo "variable BUILD_TARGET_ARCHITECTURE is not set; provide it via 'app.cfg'"
    exit 4
fi

if [ x"${BUILD_EESSI_VERSION}" == "x" ]; then
    echo "variable BUILD_EESSI_VERSION is not set; provide it via 'app.cfg'"
    exit 5
fi

env | egrep 'SOFTWARE_FILE|SCRIPTS_DIR|LOCAL_TMP|BUILD_TARGET_ARCHITECTURE|BUILD_EESSI_VERSION'

# requires some stuff from https://github.com/EESSI/software-layer
# these and other scripts of the bot should be made available in some directory or in
# some directories and the locations should then be configured in some cfg file, e.g., app.cfg
#   init/minimal_eessi_env --> stored under $SCRIPTS_DIR/init
#   init/eessi_environment_variables --> stored under $SCRIPTS_DIR/init
#   init/eessi_softwre_subdir_for_host.py --> stored under $SCRIPTS_DIR/init
#   configure_easybuild --> stored under $SCRIPTS_DIR
#   eessi_software_subdir.py --> stored under $SCRIPTS_DIR

# save some environment settings we may need after entering the Gentoo Prefix
#   softwarelist.yaml could be stored directly by EESSI bot into some job definition file
echo "export SOFTWARE_FILE=${SOFTWARE_FILE}" > _env
#   scripts dir could be a directory known through app.cfg or stored in job definition file
echo "export SCRIPTS_DIR=${SCRIPTS_DIR}" >> _env
#   only used to set EESSI_TMPDIR, could be taken from a job definition file
echo "export LOCAL_TMP=${LOCAL_TMP}" >> _env
#   probably not needed (because all information can be derived via scripts on build node, i.e.,
#   inside a job); same as "${EESSI_OS_TYPE}/${EESSI_SOFTWARE_SUBDIR}"
echo "export BUILD_TARGET_ARCHITECTURE=${BUILD_TARGET_ARCHITECTURE}" >> _env
#   could be delivered as argument, only used to set EESSI_PILOT_VERSION, the latter might be
#   set directly instead
echo "export BUILD_EESSI_VERSION=${BUILD_EESSI_VERSION}" >> _env

# the container script launches the container
export EESSI_PILOT_VERSION=${BUILD_EESSI_VERSION}
export SINGULARITY_BIND="${SCRIPTS_DIR}:${SCRIPTS_DIR},$(pwd):/eessi_bot_job"

${SCRIPTS_DIR}/build_container.sh run ${LOCAL_TMP}/${USER}/EESSI ${SCRIPTS_DIR}/run_in_compat_layer_env.sh ${SCRIPTS_DIR}/mod_EESSI_install.sh

