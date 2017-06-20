#!/usr/bin/env bash

INSTALL_FILES=".install_files.txt"
INSTALL_LOG=".install_log.log"

if [[ $# -eq 0 ]]; then
    echo "Specify whether you're trying to install or uninstall"
    echo "-i for install"
    echo "-u for uninstall"
    echo "If you didn't install with this script, then it won't be able to uninstall"
else
    ARG=$1
fi

if [[ $ARG == "-i" ]]; then
    if [[ $VIRTUAL_ENV == "" ]]; then
        echo "WARNING: Installing outside a Virtual Environment"
        echo "Proceed with installation? y/n"
        read CONTINUE
        if [[ ${CONTINUE} == "n" ]]; then
            exit 0
        fi
    else
        echo "Installing inside a Virtual Environment: ${VIRTUAL_ENV}"
    fi
    echo -n "Running setup.py..."
    python setup.py install --record $INSTALL_FILES &> $INSTALL_LOG
    EXITCODE=$?
    if [[ $EXITCODE -eq 0 ]]; then
        echo -e "\rRunning setup.py... Complete!"
        exit 0
    else
        echo -e "\rRunning setup.py... Failed."
        exit 1
    fi
elif [[ $ARG == "-u" ]]; then
    echo "Attempting to uninstall"
    if [[ -e $INSTALL_FILES ]]; then
        echo -n "Found egg files. Deleting... "
        xargs rm <$INSTALL_FILES
        echo -e "\rFound egg files. Deleting... Done!"
    else
        echo "Couldn't find the files to remove"
        echo "Did you install with this script, or did you run uninstall without installing first?"
    fi
fi


