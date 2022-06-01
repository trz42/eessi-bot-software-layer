#!/bin/bash
#
# Script to install EESSI pilot software stack (version 2021.12)
#

TOPDIR=$(dirname $(realpath $0))

source /eessi_bot_job/_env

function echo_green() {
    echo -e "\e[32m$1\e[0m"
}

function echo_red() {
    echo -e "\e[31m$1\e[0m"
}

function echo_yellow() {
    echo -e "\e[33m$1\e[0m"
}

function fatal_error() {
    echo_red "ERROR: $1" >&2
    exit 1
}

function check_exit_code {
    ec=$1
    ok_msg=$2
    fail_msg=$3

    if [[ $ec -eq 0 ]]; then
        echo_green "${ok_msg}"
    else
        fatal_error "${fail_msg}"
    fi
}

# honor $TMPDIR if it is already defined, use /tmp otherwise
if [ -z $TMPDIR ]; then
    export WORKDIR=/tmp/$USER
else
    export WORKDIR=$TMPDIR/$USER
fi

TMPDIR=$(mktemp -d)

echo ">> Setting up environment..."

source $TOPDIR/init/minimal_eessi_env

env | grep BUILD_
env | grep EESSI_

if [ -d $EESSI_CVMFS_REPO ]; then
    echo_green "$EESSI_CVMFS_REPO available, OK!"
else
    fatal_error "$EESSI_CVMFS_REPO is not available!"
fi

# make sure we're in Prefix environment by checking $SHELL
echo " compare '${SHELL}' and '${EPREFIX}/bin/bash' to verify if run inside Gentoo Prefix environment"

# need different checks depending on version (directory structure changed from 2021.06 to 2021.12)
#   or just strip '/versions' from EPREFIX if it exists
EPREFIX_SHORT=${EPREFIX/\/versions}

if [[ ${SHELL} = ${EPREFIX_SHORT}/bin/bash ]]; then
    echo_green ">> It looks like we're in a Gentoo Prefix environment, good!"
else
    fatal_error "Not running in Gentoo Prefix environment, run '${EPREFIX}/startprefix' first!"
fi

# avoid that pyc files for EasyBuild are stored in EasyBuild installation directory
export PYTHONPYCACHEPREFIX=$TMPDIR/pycache

DETECTION_PARAMETERS=''
GENERIC=0
EB='eb'
if [[ "$1" == "--generic" || "$EASYBUILD_OPTARCH" == "GENERIC" ]]; then
    echo_yellow ">> GENERIC build requested, taking appropriate measures!"
    DETECTION_PARAMETERS="$DETECTION_PARAMETERS --generic"
    GENERIC=1
    EB='eb --optarch=GENERIC'
fi

echo ">> Determining software subdirectory to use for current build host..."
export EESSI_SOFTWARE_SUBDIR_OVERRIDE=$(python3 $TOPDIR/eessi_software_subdir.py $DETECTION_PARAMETERS)

# Set all the EESSI environment variables (respecting $EESSI_SOFTWARE_SUBDIR_OVERRIDE)
# $EESSI_SILENT - don't print any messages
# $EESSI_BASIC_ENV - give a basic set of environment variables
EESSI_SILENT=1 EESSI_BASIC_ENV=1 source $TOPDIR/init/eessi_environment_variables

if [[ -z ${EESSI_SOFTWARE_SUBDIR} ]]; then
    fatal_error "Failed to determine software subdirectory?!"
elif [[ "${EESSI_SOFTWARE_SUBDIR}" != "${EESSI_SOFTWARE_SUBDIR_OVERRIDE}" ]]; then
    fatal_error "Values for EESSI_SOFTWARE_SUBDIR_OVERRIDE (${EESSI_SOFTWARE_SUBDIR_OVERRIDE}) and EESSI_SOFTWARE_SUBDIR (${EESSI_SOFTWARE_SUBDIR}) differ!"
else
    echo_green ">> Using ${EESSI_SOFTWARE_SUBDIR} as software subdirectory!"
fi

echo ">> Initializing Lmod..."
source $EPREFIX/usr/share/Lmod/init/bash
ml_version_out=$TMPDIR/ml.out
ml --version &> $ml_version_out
if [[ $? -eq 0 ]]; then
    echo_green ">> Found Lmod ${LMOD_VERSION}"
else
    fatal_error "Failed to initialize Lmod?! (see output in ${ml_version_out}"
fi

echo ">> Configuring EasyBuild..."
echo "  running from '$(pwd)'"
env | sed -e 's/^/ENV_mod_EESSI_install_ENV  /'
source $TOPDIR/configure_easybuild

echo ">> Setting up \$MODULEPATH..."
# make sure no modules are loaded
module --force purge
# ignore current $MODULEPATH entirely
module unuse $MODULEPATH
module use $EASYBUILD_INSTALLPATH/modules/all
if [[ -z ${MODULEPATH} ]]; then
    fatal_error "Failed to set up \$MODULEPATH?!"
else
    echo_green ">> MODULEPATH set up: ${MODULEPATH}"
fi

REQ_EB_VERSION='4.5.0'

echo ">> Checking for EasyBuild module..."
ml_av_easybuild_out=$TMPDIR/ml_av_easybuild.out
module avail 2>&1 | grep -i easybuild/${REQ_EB_VERSION} &> ${ml_av_easybuild_out}
if [[ $? -eq 0 ]]; then
    echo_green ">> EasyBuild module found!"
else
    echo_yellow ">> No EasyBuild module yet, installing it..."

    EB_TMPDIR=${TMPDIR}/ebtmp
    echo ">> Temporary installation (in ${EB_TMPDIR})..."
    pip_install_out=${TMPDIR}/pip_install.out
    pip3 install --prefix $EB_TMPDIR easybuild &> ${pip_install_out}

    echo ">> Final installation in ${EASYBUILD_INSTALLPATH}..."
    export PATH=${EB_TMPDIR}/bin:$PATH
    export PYTHONPATH=$(ls -d ${EB_TMPDIR}/lib/python*/site-packages):$PYTHONPATH
    eb_install_out=${TMPDIR}/eb_install.out
    eb --install-latest-eb-release &> ${eb_install_out}

    eb --search EasyBuild-${REQ_EB_VERSION}.eb | grep EasyBuild-${REQ_EB_VERSION}.eb > /dev/null
    if [[ $? -eq 0 ]]; then
        eb EasyBuild-${REQ_EB_VERSION}.eb >> ${eb_install_out} 2>&1
    fi

    module avail easybuild/${REQ_EB_VERSION} &> ${ml_av_easybuild_out}
    if [[ $? -eq 0 ]]; then
        echo_green ">> EasyBuild module installed!"
    else
        fatal_error "EasyBuild/${REQ_EB_VERSION} module failed to install?! (output of 'pip install' in ${pip_install_out}, output of 'eb' in ${eb_install_out}, output of 'ml av easybuild' in ${ml_av_easybuild_out})"
    fi
fi

echo ">> Loading EasyBuild module..."
module load EasyBuild/$REQ_EB_VERSION
eb_show_system_info_out=${TMPDIR}/eb_show_system_info.out
$EB --show-system-info > ${eb_show_system_info_out}
if [[ $? -eq 0 ]]; then
    echo_green ">> EasyBuild seems to be working!"
    $EB --version | grep "${REQ_EB_VERSION}"
    if [[ $? -eq 0 ]]; then
        echo_green "Found EasyBuild version ${REQ_EB_VERSION}, looking good!"
    else
        $EB --version
        fatal_error "Expected to find EasyBuild version ${REQ_EB_VERSION}, giving up here..."
    fi
    $EB --show-config
else
    cat ${eb_show_system_info_out}
    fatal_error "EasyBuild not working?!"
fi

echo_green "All set, let's start installing some software in ${EASYBUILD_INSTALLPATH}..."


ls -lR /eessi_bot_job

ok_msg="Wow the whole stack installed with a single line of magic!"
fail_msg="Oh oh, now how do we find out what went wrong ..."
$EB --easystack /eessi_bot_job/${SOFTWARE_FILE} --experimental
check_exit_code $? "${ok_msg}" "${fail_msg}"


echo ">> Creating/updating Lmod cache..."
export LMOD_RC="${EASYBUILD_INSTALLPATH}/.lmod/lmodrc.lua"
if [ ! -f $LMOD_RC ]; then
    python3 $TOPDIR/create_lmodrc.py ${EASYBUILD_INSTALLPATH}
    check_exit_code $? "$LMOD_RC created" "Failed to create $LMOD_RC"
fi

# we need to specify the path to the Lmod cache dir + timestamp file to ensure
# that update_lmod_system_cache_files updates correct Lmod cache
lmod_cache_dir=${EASYBUILD_INSTALLPATH}/.lmod/cache
lmod_cache_timestamp_file=${EASYBUILD_INSTALLPATH}/.lmod/cache/timestamp
modpath=${EASYBUILD_INSTALLPATH}/modules/all

${LMOD_DIR}/update_lmod_system_cache_files -d ${lmod_cache_dir} -t ${lmod_cache_timestamp_file} ${modpath}
check_exit_code $? "Lmod cache updated" "Lmod cache update failed!"

ls -lrt ${EASYBUILD_INSTALLPATH}/.lmod/cache

echo ">> Checking for missing installations..."
ok_msg="No missing installations, party time!"
fail_msg="On no, some installations are still missing, how did that happen?!"
eb_missing_out=$TMPDIR/eb_missing.out
#$EB --easystack eessi-${EESSI_PILOT_VERSION}.yml --experimental --missing --robot $EASYBUILD_PREFIX/ebfiles_repo | tee ${eb_missing_out}
$EB --easystack /eessi_bot_job/${SOFTWARE_FILE} --experimental --missing --robot $EASYBUILD_PREFIX/ebfiles_repo | tee ${eb_missing_out}
grep "No missing modules" ${eb_missing_out} > /dev/null
check_exit_code $? "${ok_msg}" "${fail_msg}"

echo ">> Cleaning up ${TMPDIR}..."
rm -r ${TMPDIR}
