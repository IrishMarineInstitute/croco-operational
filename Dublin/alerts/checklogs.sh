#!/bin/bash
cd "$(dirname "$0")";

ADMIN="hpc.support@marine.ie"

checklog () {
docker cp $1:/log/app.log $1
if grep $1 -e "Exception"; then
	echo "Log File Attached" | mutt -s "ALERT: Error in $1" -a $1 -- $ADMIN
fi
rm $1; docker exec $1 rm -rf /log/app.log
}

checklog "ecmwf"
checklog "bulk-daily"
checklog "bulk-fcnc"
checklog "bulk-weekly"
checklog "boundary"
checklog "rivers"
checklog "input-forecast"
checklog "input-hindcast"

