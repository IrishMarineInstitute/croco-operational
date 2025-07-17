from netCDF4 import Dataset, num2date
from datetime import datetime
import argparse
import glob
import os

msg = '''Given a BASENAME (-b) (e.g. "DUBLIN_"), an absolute PATH (-p) and baseline REFERENCE (-r) for CROCO time (e.g. "19680523"), this 
         function renames CROCO stations files to a more human-readable format for archiving, such as DUBLIN_20250530.nc '''

def main(): 

    # Initialize argument parser
    parser = argparse.ArgumentParser(description=msg)
    # Define command-line arguments
    parser.add_argument('-b', '--Basename', help='Prefix for output, archived CROCO files')
    parser.add_argument('-p', '--Path', help='Output path for CROCO files')
    parser.add_argument('-r', '--Reference', help='Reference baseline for time used in CROCO')

    # Read arguments from command line
    args = parser.parse_args()
    if args.Basename:
        basename = args.Basename
    else:
        return

    if args.Path:
        path = args.Path
    else:
        return

    if args.Reference:
        units = datetime.strptime(args.Reference, '%Y%m%d')
    else:
        return

    # Get list of CROCO history files as copied from HPC
    files = sorted(glob.glob(path + '/stations.*.nc'))

    for f in files:
        with Dataset(f, 'r') as nc: # Open NetCDF
            time = num2date(nc.variables['scrum_time'][:], 'seconds since ' + units.strftime('%Y-%m-%d')) # Read time 
        # Rename file using date from first time stamp
        name = path + '/' + basename + time[0].strftime('%Y%m%d') + '.nc'
        # Rename and continue with next history file
        os.rename(f, name)

if __name__ == '__main__':
    main()
