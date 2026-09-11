#!/bin/bash

export SOURCE_DIR=/ec/project/accord/tactus/
export REFERENCE=cy50t2/reference.json
export IGNORE=cy50t2/.ignore
export GREEN=cy50t2/.green

python checker.py --generate --folder $SOURCE_DIR --json $REFERENCE  --ignore $IGNORE --green $GREEN




