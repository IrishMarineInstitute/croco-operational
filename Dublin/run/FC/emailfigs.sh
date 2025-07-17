#!/bin/bash

. config # Declare useful variables

ADMIN="hpc.support@marine.ie"

# Email time series plots to administrator to check everything went fine
${PYEXE} finalcheck.py -b ${basename} -p ${agghis} -r "${reference}" -x ${hislon} -y ${hislat}
if grep log -e "Exception"; then
	echo "Log File Attached" | mutt -s "ALERT: Error while checking HISTORY" -a log -- $ADMIN
else
	echo "Figures Attached" | mutt -s "DUBLIN HISTORY FIGURES" -a HIS-zeta.png -a HIS-salt.png -a HIS-temp.png -- $ADMIN
fi
rm log; rm *.png

${PYEXE} finalcheck.py -b ${basename} -p ${aggavg} -r "${reference}" -x ${hislon} -y ${hislat}
if grep log -e "Exception"; then
	echo "Log File Attached" | mutt -s "ALERT: Error while checking AVERAGES" -a log -- $ADMIN
else
	echo "Figures Attached" | mutt -s "DUBLIN AVERAGES FIGURES" -a AVG-chl.png -a AVG-salt.png -a AVG-temp.png -- $ADMIN
fi
rm log; rm *.png
