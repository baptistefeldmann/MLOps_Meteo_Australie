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
SCRIPT_PY="$SCRIPT_DIR/background_satellite_images.py"
# Project path
PROJ_PATH="$SCRIPT_DIR/../.."


#----------------------------- Input parameters ------------------------------
# 1 --aoi_patches_file     type=str              [required]
# 2 --outFolder            type=str              [required]
# 3 --dluFolder            type=str              [required]

#--------------------------------- Check args --------------------------------
if [ "$#" -lt 3 ]; then
    echo
    echo "Illegal number of parameters. Must be 3"
    echo
    exit 1
fi

#-------------------------------- Run docker ---------------------------------
bash $PROJ_PATH/docker/run.sh "python $SCRIPT_PY $1 $2 $3"

# Return exit code
err_code=$?
echo return code: $err_code
exit $err_code