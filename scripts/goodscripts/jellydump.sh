#!/bin/bash

for i in $(cat ${1})
do
	echo $i
	cd $i
	jellyfish dump mercounts15.jf -o counts15.fa
	jellyfish dump mercounts31.jf -o counts31.fa
	cd ..
done
