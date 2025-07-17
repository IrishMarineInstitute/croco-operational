from datetime import datetime, timedelta
from netCDF4 import Dataset, num2date
import argparse
import glob
import os

msg = ''' This function looks at local CROCO restart files and retains the one needed for tomorrow's forecast run.
          This file is renamed as "croco_ini.nc" and sent back to the HPC.  '''

def main():
    ''' 
    This script inspects the CROCO restart files just generated
    during the last forecast run, and determines which restart
    file should be used for tomorrow's forecast run.
    '''

    # Initialize argument parser
    parser = argparse.ArgumentParser(description=msg)
    # Define command-line arguments
    parser.add_argument('-d', '--Date', help='Date when forecast was initiated')
    parser.add_argument('-r', '--Reference', help='Reference baseline for time used in CROCO')

    # Read arguments from command line
    args = parser.parse_args()
    if args.Date:
        today = datetime.strptime(args.Date, '%Y-%m-%d')
    else:
        return

    if args.Reference:
        units = 'seconds since ' + datetime.strptime(args.Reference, '%Y%m%d').strftime('%Y-%m-%d')
    else:
        return

    # Target date. Tomorrow's restart file must contain this date
    target = today + timedelta(days=2) 

    files = sorted(glob.glob('croco_rst.*.nc'))
    for f in files:
        with Dataset(f, 'r') as nc:
            time = num2date(nc.variables['time'][-1], units)
        time = datetime(time.year, time.month, time.day)
        
        if time == target:
            # This is the right file, let's rename it as "croco_ini.nc"
            os.rename(f, 'croco_ini.nc')
        else:
            # We don't need this file
            os.remove(f)

    if not os.path.isfile('croco_ini.nc'):
        print(0) # Oh no! There's no restart file for tomorrow
    
    print(1) # All good

if __name__ == '__main__':
    main()

