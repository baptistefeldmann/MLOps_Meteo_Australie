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

#----------------------------- Input parameters ------------------------------
# 1 --city                 type=str              [required]

#--------------------------------- Check args --------------------------------
if [ "$#" -lt 1 ]; then
    echo
    echo "Illegal number of parameters. Must be 1"
    echo
    exit 1
fi

#-------------------------------- Run docker ---------------------------------
docker run collect-data:1.0 --volumes  --mode inference $1
docker run train-pred:1.0 "python $SRC_CODE_DIR/models/predict.py $1"

# Return exit code
err_code=$?
echo return code: $err_code
exit $err_code