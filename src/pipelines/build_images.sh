#!/bin/bash

echo
echo "-----------------------------------------------------------------------"
echo "                           ${BASH_SOURCE##*/}                          "
echo "-----------------------------------------------------------------------"
echo

#------------------------------ Constant Params ------------------------------
# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
# Python script name
SRC_CODE_DIR="$SCRIPT_DIR/.."

# Build Docker images
docker build collect-data $SRC_CODE_DIR/data
docker build train-pred $SRC_CODE_DIR/models

# Return exit code
err_code=$?
echo return code: $err_code
exit $err_code