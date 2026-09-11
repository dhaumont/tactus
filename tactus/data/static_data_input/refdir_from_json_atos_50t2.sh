#!/bin/bash

export TARGET_DIR=/lus/h2resw01/scratch/cvap/tactus
export REFERENCE=cy50t2/reference.json

echo "Generate ln-all.sh containing the instruction to copy the files from the reference $REFERENCE into $TARGET_DIR"
python checker.py  --folder $TARGET_DIR --json $REFERENCE --cmd > ln-all.sh

#Uncomment to execute the actual creation
#source ln-all.sh

 echo "Check the status of $TARGET_DIR correspond to $REFERENCE definition"
 python checker.py  --folder $TARGET_DIR --json $REFERENCE


