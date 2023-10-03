#!/bin/bash
#
# GitHub App for the EESSI project
#
# A bot to help with requests to add software installations to the EESSI software layer,
# see https://github.com/EESSI/software-layer

# This script cleans up (deletes) all build artefacts and temporary storage tarballs of a given PR
#
# author: Thomas Roeblitz (@trz42)
#
# license: GPLv2
#

SCRIPT_DIR=$(dirname $(realpath $BASH_SOURCE))

function display_help
{
  echo "Usage: $0 [OPTIONS] <PR number>"                                                >&2
  echo "  -b | --jobs-base-dir DIRECTORY  -  jobs base directory [default: reads"       >&2
  echo "                                     value from bot config file app.cfg or .]"  >&2
  echo "  -D | --dry-run                  -  only show commands that would be run"      >&2
  echo "                                     [default: false]"                          >&2
  echo "  -h | --help                     -  display this usage information"            >&2
}

function get_jobs_base_dir
{
  app_cfg_path=${1}
  grep jobs_base_dir ${app_cfg_path} | grep -v '^[ ]*#' | sed -e 's/^[^=]*=[ ]*//'
}

echo

if [[ $# -lt 1 ]]; then
    display_help
    exit 1
fi

# process command line args
POSITIONAL_ARGS=()

jobs_base_dir=
dry_run=false

while [[ $# -gt 0 ]]; do
  case $1 in
    -b|--jobs-base-dir)
      if [[ $# -gt 1 ]]; then
        jobs_base_dir="$2"
        shift 2
      else
        echo "Error: missing argument (directory) for parameter '${1}'"
        exit 2
      fi
      ;;
    -D|--dry-run)
      dry_run=true
      shift 1
      ;;
    -h|--help)
      display_help
      exit 0
      ;;
    -*|--*)
      echo "Error: Unknown option: $1" >&2
      exit 1
      ;;
    *)  # No more options
      POSITIONAL_ARGS+=("$1") # save positional arg
      shift
      ;;
  esac
done

# restore potentially parsed filename(s) into $*
set -- "${POSITIONAL_ARGS[@]}"

if [[ $# -ne 1 ]]; then
    echo "Error: exactly one PR number should be provided as argument"
    display_help
    exit 3
fi

pull_request=${1}

if ${dry_run} = true ; then
  echo "DRY_RUN: not removing any files"
fi

# determine jobs base dir if not given explicitly
# 1. check for file app.cfg in SCRIPT_DIR
# 2. check for file app.cfg in current dir
# if found try to obtain value of jobs_base_dir setting
# if not file not found or jobs_base_dir setting not found (or empty) --> error & exit
if [[ -z ${jobs_base_dir} ]]; then
  echo "jobs base directory not given explicitly, trying to determine it"
  if [[ -e ${SCRIPT_DIR}/app.cfg ]]; then
    echo "check for app.cfg in '${SCRIPT_DIR}'"
    jobs_base_dir=$(get_jobs_base_dir ${SCRIPT_DIR}/app.cfg)
  else
    if [[ -e ./app.cfg ]]; then
      echo "check for app.cfg in '${PWD}' (current directory)"
      jobs_base_dir=$(get_jobs_base_dir ./app.cfg)
    fi
  fi
fi
if [[ -z ${jobs_base_dir} ]]; then
  echo "Error: jobs base directory is empty, please specify it as argument"
  display_help
  exit 4
fi

echo "processing all directories for PR ${pull_request}:"
find ${jobs_base_dir}/* -maxdepth 1 -type d -wholename */pr_${pull_request} | sed -e 's/^/  /'

echo
echo "disk usage of directories for PR ${pull_request} BEFORE removing build artefacts and tmp storage"
for d in $(find ${jobs_base_dir}/* -maxdepth 1 -type d -wholename */pr_${pull_request}); do du -sh $d; done

echo
echo "$([[ ${dry_run} = true ]] && echo "DRY_RUN: ")removing tmp storage tarballs for PR ${pull_request}"
for d in $(find ${jobs_base_dir}/* -maxdepth 1 -type d -wholename */pr_${pull_request})
do
  for f in $(find $d -type f -wholename "*[0-9].tgz")
  do
    if ${dry_run} = true ; then
      echo "DRY_RUN: rm '$f' ($(ls -lh $f | awk '{print $5}'))"
    else
      echo "Removing file '$f'"
      rm $f
    fi
  done
done

echo
echo "disk usage of directories for PR ${pull_request} AFTER removing tmp storage tarballs"
for d in $(find ${jobs_base_dir}/* -maxdepth 1 -type d -wholename */pr_${pull_request}); do du -sh $d; done

echo
echo "$([[ ${dry_run} = true ]] && echo "DRY_RUN: ")removing build artefacts for PR ${pull_request}"
for d in $(find ${jobs_base_dir}/* -maxdepth 1 -type d -wholename */pr_${pull_request})
do
  for f in $(find $d -type f -wholename "*tar.gz")
  do
    if ${dry_run} = true ; then
      echo "DRY_RUN: rm '$f' ($(ls -lh $f | awk '{print $5}'))"
    else
      echo "Removing file '$f'"
      rm $f
    fi
  done
done

echo
echo "disk usage of directories for PR ${pull_request} AFTER removing build artefacts and tmp storage"
for d in $(find ${jobs_base_dir}/* -maxdepth 1 -type d -wholename */pr_${pull_request}); do du -sh $d; done

