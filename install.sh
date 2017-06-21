#!/usr/bin/env bash
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'
PACKAGE="pyro4tunneling"
PACKAGE_NAME="${BLUE}${PACKAGE}${NC}"
INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INSTALL_FILES="${INSTALL_DIR}/install_files_${PACKAGE_NAME}.txt"
INSTALL_LOG="${INSTALL_DIR}/install_log_${PACKAGE_NAME}.log"

function checkVirutalEnv {
    if [[ ${VIRTUAL_ENV} == "" ]]; then
        echo -e "${RED}WARNING:${NC} Installing outside a Virtual Environment"
        echo "Proceed with installation? y/n"
        read CONTINUE
        if [[ ${CONTINUE} == "n" ]]; then
            exit 0
        fi
    else
        echo -e "Installing ${PACKAGE_NAME} inside a Virtual Environment: ${BLUE}${VIRTUAL_ENV}${NC}"
    fi
}

if [[ $# -eq 0 ]]; then
    echo "Specify whether you're trying to install or uninstall"
    echo "-i for install"
    echo "-u for uninstall"
    echo "If you didn't install with this script, then it won't be able to uninstall"
else
    ARG=$1
fi

if [[ ${ARG} == "-i" ]]; then
    checkVirutalEnv
    echo -n "Running setup.py..."
    cd ${INSTALL_DIR}
    python setup.py install --record ${INSTALL_FILES} >>${INSTALL_LOG} 2>&1
    EXITCODE=$?
    if [[ ${EXITCODE} -eq 0 ]]; then
        echo -e "\rRunning setup.py... ${GREEN}Complete!${NC}"
        exit 0
    else
        echo -e "\rRunning setup.py... ${RED}Failed.${NC}"
        exit 1
    fi
elif [[ ${ARG} == "-u" ]]; then
    echo -e "Attempting to uninstall ${PACKAGE_NAME}"
    if [[ -e ${INSTALL_FILES} ]]; then
        echo -n "Found egg files. Deleting... "
        xargs rm <${INSTALL_FILES}
        echo -e "\rFound egg files. Deleting... ${GREEN}Done!${NC}"
    else
        echo "Couldn't find the files to remove"
        echo "Did you install with this script, or did you run uninstall without installing first?"
    fi
fi


