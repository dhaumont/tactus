#!/bin/bash

export TARGET_DIR=/leonardo_work/DestE_330_26/users/SAN/static/DEODE
export REFERENCE=cy49t2/reference.json
python checker.py  --folder $TARGET_DIR --json $REFERENCE 


