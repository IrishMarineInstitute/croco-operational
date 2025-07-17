#!/bin/bash
cd "$(dirname "$0")";

FC="Dublin-FC" # Name of forecast CROCO directory under "configs"

if [ -e "croco.in" ]
then
	if ! pgrep -x "mpirun" > /dev/null 
	then
		rm OUTPUT/*.nc # Remove last week's hindcast
		# croco.in received! Run the model!
		mpirun -np 40 ./croco croco.in > log; rm croco.in
		# Removing croco.in makes sure that model run isn't launched again.
		# Now, move to OUTPUT directory to handle RESTART files
		cd OUTPUT;
		# For the HINDCAST, we're only interested in the 
		# last RESTART file. The following instruction
		# deletes all restart files except for the last one.
		ls croco_rst.*.nc -t | tail -n +2 | xargs rm --
		# Now, this RESTART file will play two roles: 
		# (a) It becomes the INITIAL file of next week's hindcast
		cp croco_rst.*.nc ../INPUT/croco_ini.nc
		# (b) It is also the INITIAL file of the FORECAST catch-up run
		# In this case, it replaces the restart file generated from 
		# last night's forecast. Make sure to specify the name of the
		# forecast CROCO directory at the top of this script.
		mv croco_rst.*.nc "../../${FC}/INPUT/croco_ini.nc"
		# So, tonight's forecast will be a continuation of the hindcast.
		# This is the weekly forecast catch-up run, which is used to prevent
		# the forecasts to drift away from the hindcast's numerical solution.

		# This process runs weekly. The rest of the week, forecast will start
		# on the next midnight, and run for +3 days. Here, the forecast starts
		# on day -2 and runs for +5 days (forecast catch-up run).
        fi
fi
