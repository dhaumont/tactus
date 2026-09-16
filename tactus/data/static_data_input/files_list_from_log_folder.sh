#!/bin/bash
export LOG_DIR=$1
export OUTPUT_FILE=$2
export ROOT_DIR=$3
export ECFLOW_NAME="${HOME}/tactus_ecflow"

echo "files_list_from_log_folder.sh:"
echo LOG_DIR=$LOG_DIR
echo OUTPUT_FILE=$OUTPUT_FILE
echo ROOT_DIR=$ROOT_DIR
echo ECFLOW_NAME=$ECFLOW_NAME

find ${LOG_DIR}  -type l | xargs ls -all | grep  ${ROOT_DIR} | cut -d'>' -f2 > ${OUTPUT_FILE}.tmp
find ${ECFLOW_NAME} -name "*.1" | xargs grep ${ROOT_DIR} | grep "| INFO" | cut -d'|' -f3 | grep "ln -sf" | cut -d' ' -f4 >> ${OUTPUT_FILE}.tmp
find ${ECFLOW_NAME} -name "*.1" | xargs grep ${ROOT_DIR} | grep -v "| INFO" | grep "ln -s"|cut -d' ' -f6 >> ${OUTPUT_FILE}.tmp
find ${ECFLOW_NAME} -name "*.1" | xargs grep ${ROOT_DIR} | grep  " cp " | cut -d'|' -f3 | cut -d' ' -f3 >> ${OUTPUT_FILE}.tmp
find ${ECFLOW_NAME} -name "*.1" | xargs grep ${ROOT_DIR} | grep  "\->" | cut -d'>' -f2 >> ${OUTPUT_FILE}.tmp

cat ${OUTPUT_FILE}.tmp |  sed -e "s|${ROOT_DIR}/||g" | sed -e "s|//|/|g"|sed -e "s/^ //g"| sort | uniq > ${OUTPUT_FILE}
rm ${OUTPUT_FILE}.tmp

