#!/bin/bash
export SOURCE_DIR=/ec/project/accord/tactus
export GREEN=cy50t2/.green

find $SCRATCH/tactus  -type l | xargs ls -all | grep  $SOURCE_DIR | cut -d'>' -f2 > $GREEN.tmp
find $HOME/tactus_ecflow -name "*.1" | xargs grep $SOURCE_DIR | grep "| INFO" | cut -d'|' -f3 | grep "ln -sf" | cut -d' ' -f4 >> $GREEN.tmp
find $HOME/tactus_ecflow -name "*.1" | xargs grep $SOURCE_DIR | grep -v "| INFO" | grep "ln -s"|cut -d' ' -f6 >> $GREEN.tmp
find $HOME/tactus_ecflow -name "*.1" | xargs grep $SOURCE_DIR | grep  " cp " | cut -d'|' -f3 | cut -d' ' -f3 >> $GREEN.tmp
find $HOME/tactus_ecflow -name "*.1" | xargs grep $SOURCE_DIR | grep  "\->" | cut -d'>' -f2 >> $GREEN.tmp


echo "$SOURCE_DIR/climate/GMTED2010" >> $GREEN.tmp
cat $GREEN.tmp |  sed -e "s|$SOURCE_DIR/||g" | sed -e "s|//|/|g"|sed -e "s/^ //g"| sort | uniq > $GREEN
rm $GREEN.tmp

