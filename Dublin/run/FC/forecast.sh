#!/bin/bash
cd "$(dirname "$0")";

. config # Declare useful variables

today=$(date +%F)

checkconfig () {
docker cp $1:/log/$1.config .
. $1.config
rm $1.config
}

checkconfig "boundary"
checkconfig "rivers"

##########################################################################################
#                                                                                        #
#                        SECTION 1: COPYING FORCING FILES TO HPC                         #
#                                                                                        #
##########################################################################################

# BOUNDARY
docker cp boundary:${bryname} . # Copy from container
sshpass -p ${password} scp croco_bry.nc ${username}@${ip}:"${hpcdir}INPUT" # Copy to HPC
rm croco_bry.nc # Remove local file

# RUNOFF 
docker cp rivers:${runoffname} . # Copy from container
sshpass -p ${password} scp croco_runoff.nc ${username}@${ip}:"${hpcdir}INPUT" # Copy to HPC
rm croco_runoff.nc # Remove local file

# CROCO.in
docker cp input-forecast:/root/croco.in . # Copy from container
sshpass -p ${password} scp croco.in ${username}@${ip}:${hpcdir} # Copy to HPC
rm croco.in # Remove local file

# ONLINE BULK FORCING
docker cp bulk-fcnc:/log/bulk-fcnc-abspath.config .
input="bulk-fcnc-abspath.config"
while IFS= read -r line
do
	docker cp bulk-fcnc:$line . # Copy from container
done < "$input"
rm "$input"

docker cp bulk-fcnc:/log/bulk-fcnc-basename.config .
input="bulk-fcnc-basename.config"
while IFS= read -r line
do
	sshpass -p ${password} scp ${line} ${username}@${ip}:"${hpcdir}DATA/ERA5" # Copy to HPC
	rm ${line} # Remove local file
done < "$input"
rm "$input"

##########################################################################################
#                                                                                        #
#                                SECTION 2: RUNNING MODEL                                #
#                                                                                        #
##########################################################################################

sleep 10800 # Wait for model to run

# Operations are now controlled by run.sh script on HPC

ADMIN="hpc.support@marine.ie"

sshpass -p ${password} scp ${username}@${ip}:"${hpcdir}log" . # Get CROCO log file from HPC

if grep log -e "MAIN: DONE"; then # Run was successful
	echo "Run was successful" | mutt -s "DUBLIN FC Finished Successfully!" -- $ADMIN
else                              # Run failed
	echo "Log File Attached"  | mutt -s "WARNING! DUBLIN FC Failed" -a log -- $ADMIN
fi
rm log; # Remove log file locally

sshpass -p ${password} ssh ${username}@${ip} rm -f "${hpcdir}log" # Remove log file in HPC

##########################################################################################
#                                                                                        #
#                       SECTION 3: COPYING FORCING FILES FROM HPC                        #
#                                                                                        #
##########################################################################################

sshpass -p ${password} scp ${username}@${ip}:"${hpcdir}OUTPUT/croco_his.*.nc"  "${outputhis}" 
sshpass -p ${password} scp ${username}@${ip}:"${hpcdir}OUTPUT/croco_avg.*.nc"  "${outputavg}" 
sshpass -p ${password} scp ${username}@${ip}:"${hpcdir}OUTPUT/stations.*.nc"   "${outputstn}" 

# Rename CROCO history files to include date
${PYEXE} rename.py -b ${basename}HIS_ -p "${outputhis}" -r "${reference}"  
${PYEXE} rename.py -b ${basename}AVG_ -p "${outputavg}" -r "${reference}"  
${PYEXE} rensta.py -b ${basename}STA_ -p "${outputstn}" -r "${reference}"  

# Clean HPC: Remove input forcing files
sshpass -p ${password} ssh ${username}@${ip} rm -f "${hpcdir}croco.in" 
sshpass -p ${password} ssh ${username}@${ip} rm -f "${hpcdir}INPUT/croco_bry.nc" 
sshpass -p ${password} ssh ${username}@${ip} rm -f "${hpcdir}INPUT/croco_runoff.nc" 
sshpass -p ${password} ssh ${username}@${ip} rm -f "${hpcdir}DATA/ERA5/*.nc" 

# Copy CROCO restart files to current directory
sshpass -p ${password} scp ${username}@${ip}:"${hpcdir}OUTPUT/croco_rst.*.nc" . 
# Find out which restart file should be used for next forecast run
RST=$($PYEXE restart.py -d $today -r $reference)
if [ $RST -eq 1 ]; then
	# Send restart file to HPC
	sshpass -p ${password} scp croco_ini.nc ${username}@${ip}:"${hpcdir}INPUT" # Copy to HPC
else
	echo "Error while producing CROCO FC restart"  | mutt -s "WARNING! No DUBLIN FC Restart File" -- $ADMIN
fi

# Remove local croco_ini.nc
rm croco_ini.nc; 

##########################################################################################
#                                                                                        #
#                   SECTION 4: CREATING PRODUCTS (THREDDS, WEBSITE, ETC.)                #
#                                                                                        #
##########################################################################################

# Create history aggregated (HC + FC) dataset for THREDDS publication
${PYEXE} aggregated.py -b ${basename}HIS_ -f "${outputhis}" -i "${hchis}" -o "${agghis}" -n $N
# Create averages aggregated (HC + FC) dataset for THREDDS publication
${PYEXE} aggregated.py -b ${basename}AVG_ -f "${outputavg}" -i "${hcavg}" -o "${aggavg}" -n $N

# Email time series plots to administrator to check everything went fine
./emailfigs.sh &> email.log

# Make CROCO files compliant with OpenDrift
${PYEXE} cf.py -i "${agghis}" -o "${aggod}" -r "${reference}"

# Clean THREDDS (HISTORY)
ssh thredds rm "${threddshis}*.nc"
# Copy files to THREDDS (HISTORY)
scp ${agghis}*.nc thredds:"${threddshis}"

# Clean THREDDS (AVERAGES)
ssh thredds rm "${threddsavg}*.nc"
# Copy files to THREDDS (AVERAGES)
scp ${aggavg}*.nc thredds:"${threddsavg}"

# Clean THREDDS (OPENDRIFT)
ssh thredds rm "${threddsod}*.nc"
# Copy files to THREDDS (OPENDRIFT)
scp ${aggod}*.nc thredds:"${threddsod}"

# Clean FC directory
cd $outputhis; ls *.nc -t | tail -n +10 | xargs rm --
cd $outputavg; ls *.nc -t | tail -n +10 | xargs rm --
cd $outputstn; ls *.nc -t | tail -n +10 | xargs rm --
