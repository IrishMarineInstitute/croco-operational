#!/bin/bash
cd "$(dirname "$0")";
if [ -e "croco.in" ]
then
	if ! pgrep -x "mpirun" > /dev/null 
	then
		rm OUTPUT/*.nc # Remove yesterday's forecast
		mpirun -np 40 ./croco croco.in > log; rm croco.in
        fi
fi
