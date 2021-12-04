#!/bin/bash

for i in $(cat ${1})
do
  echo $i
  cd $i
  echo '15'
  wc -l counts15.fa
  grep -o 1 counts15.fa | wc -l 
  echo '31'
  wc -l counts31.fa
  grep -o 1 counts15.fa | wc -l
  cd ..
done
