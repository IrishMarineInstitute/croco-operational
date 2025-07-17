#!/bin/bash
cd "$(dirname "$0")";

. config # Declare useful variables

checkconfig () {
docker cp $1:/log/$1.config .
. $1.config
rm $1.config
}

checkconfig "boundary"
checkconfig "rivers"
checkconfig "input-hindcast"

mkdir "${inputdir}${date}" # Create INPUT directory in NAS
mkdir "${outputhis}${date}" # Create OUTPUT directory in NAS
mkdir "${outputavg}${date}" # Create OUTPUT directory in NAS
mkdir "${outputstn}${date}" # Create OUTPUT directory in NAS

##########################################################################################
#                                                                                        #
#                        SECTION 1: COPYING FORCING FILES TO HPC                         #
#                                                                                        #
##########################################################################################

# BOUNDARY
docker cp boundary:${bryname} . # Copy from container
cp croco_bry.nc "${inputdir}${date}" # Copy to NAS
sshpass -p ${password} scp croco_bry.nc ${username}@${ip}:"${hpcdir}INPUT" # Copy to HPC
rm croco_bry.nc # Remove local file

# RUNOFF 
docker cp rivers:${runoffname} . # Copy from container
cp croco_runoff.nc "${inputdir}${date}" # Copy to NAS
sshpass -p ${password} scp croco_runoff.nc ${username}@${ip}:"${hpcdir}INPUT" # Copy to HPC
rm croco_runoff.nc # Remove local file

# CROCO.in
docker cp input-hindcast:/root/croco.in . # Copy from container
cp croco.in "${inputdir}${date}" # Copy to NAS
sshpass -p ${password} scp croco.in ${username}@${ip}:${hpcdir} # Copy to HPC
rm croco.in # Remove local file

# ONLINE BULK FORCING
docker cp bulk-weekly:/log/bulk-weekly-abspath.config .
input="bulk-weekly-abspath.config"
while IFS= read -r line
do
	docker cp bulk-weekly:$line . # Copy from container
done < "$input"
rm "$input"

docker cp bulk-weekly:/log/bulk-weekly-basename.config .
input="bulk-weekly-basename.config"
while IFS= read -r line
do
	cp ${line} "${inputdir}${date}" # Copy to NAS
	sshpass -p ${password} scp ${line} ${username}@${ip}:"${hpcdir}DATA/ERA5" # Copy to HPC
	rm ${line} # Remove local file
done < "$input"
rm "$input"

##########################################################################################
#                                                                                        #
#                                SECTION 2: RUNNING MODEL                                #
#                                                                                        #
##########################################################################################

sleep 12600 # Wait for model to run

# Operations are now controlled by run.sh script on HPC

ADMIN="hpc.support@marine.ie"

sshpass -p ${password} scp ${username}@${ip}:"${hpcdir}log" . # Get CROCO log file from HPC

if grep log -e "MAIN: DONE"; then # Run was successful
	echo "Run was successful" | mutt -s "DUBLIN HC Finished Successfully!" -- $ADMIN
else                              # Run failed
	echo "Log File Attached"  | mutt -s "WARNING! DUBLIN HC Failed" -a log -- $ADMIN
fi
rm log; # Remove log file locally

sshpass -p ${password} ssh ${username}@${ip} rm -f "${hpcdir}log" # Remove log file in HPC

##########################################################################################
#                                                                                        #
#                       SECTION 3: COPYING OUTPUT FILES FROM HPC                         #
#                                                                                        #
##########################################################################################

sshpass -p ${password} scp ${username}@${ip}:"${hpcdir}OUTPUT/croco_his.*.nc"  "${outputhis}${date}" 
sshpass -p ${password} scp ${username}@${ip}:"${hpcdir}OUTPUT/croco_avg.*.nc"  "${outputavg}${date}" 
sshpass -p ${password} scp ${username}@${ip}:"${hpcdir}OUTPUT/stations.*.nc"   "${outputstn}${date}" 

# Rename CROCO history files to include date
${PYEXE} rename.py -b ${basename}HIS_ -p "${outputhis}${date}" -r "${reference}"  
${PYEXE} rename.py -b ${basename}AVG_ -p "${outputavg}${date}" -r "${reference}"  
${PYEXE} rensta.py -b ${basename}STN_ -p "${outputstn}${date}" -r "${reference}"  

# Clean HPC: Remove input forcing files
sshpass -p ${password} ssh ${username}@${ip} rm -f "${hpcdir}croco.in" 
sshpass -p ${password} ssh ${username}@${ip} rm -f "${hpcdir}INPUT/croco_bry.nc" 
sshpass -p ${password} ssh ${username}@${ip} rm -f "${hpcdir}INPUT/croco_runoff.nc" 
sshpass -p ${password} ssh ${username}@${ip} rm -f "${hpcdir}DATA/ERA5/*.nc" 

# Email time series plots to administrator to check everything went fine
${PYEXE} finalcheck.py -b ${basename} -p "${outputhis}${date}" -r "${reference}" -x ${hislon} -y ${hislat}
if grep log -e "Exception"; then
	echo "Log File Attached" | mutt -s "ALERT: Error while checking HC HISTORY" -a log -- $ADMIN
else
	echo "Figures Attached" | mutt -s "DUBLIN HC HISTORY FIGURES" -a HIS-zeta.png -a HIS-salt.png -a HIS-temp.png -- $ADMIN
fi
rm log; rm *.png

${PYEXE} finalcheck.py -b ${basename} -p "${outputstn}${date}" -r "${reference}" -x ${stlon} -y ${stlat}
if grep log -e "Exception"; then
	echo "Log File Attached" | mutt -s "ALERT: Error while checking HC STATIONS" -a log -- $ADMIN
else
	echo "Figures Attached" | mutt -s "DUBLIN HC STATIONS FIGURES" -a ST-zeta.png -a ST-salt.png -a ST-temp.png -- $ADMIN
fi
rm log; rm *.png
