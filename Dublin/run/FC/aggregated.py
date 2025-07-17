from datetime import datetime, timedelta
from pathlib import Path
import argparse
import shutil
import glob
import os

msg = '''This script controls the files in the aggregated (HC + FC) archive that are published on THREDDS '''

def main(): 

    # Initialize argument parser
    parser = argparse.ArgumentParser(description=msg)
    # Define command-line arguments
    parser.add_argument('-b', '--Basename', help='Prefix of CROCO history file names (e.g. DUBLIN_)')
    parser.add_argument('-f', '--Forecastdir', help='Input directory to search for CROCO FC files')
    parser.add_argument('-i', '--Inputdir', help='Input directory to search for CROCO HC files recursively')
    parser.add_argument('-o', '--Outputdir', help='Output directoy to save the aggregated archive (HC + FC) for THREDDS')
    parser.add_argument('-n', '--N', help='Number of days back to keep in THREDDS archive')

    # Read arguments from command line
    args = parser.parse_args()
    if args.Basename:
        basename = args.Basename
    else:
        return

    if args.Forecastdir:
        fcpath = args.Forecastdir
    else:
        return

    if args.Inputdir:
        hcpath = args.Inputdir
    else:
        return

    if args.Outputdir:
        opath = args.Outputdir
    else:
        return

    if args.N:
        N = int(args.N)
    else:
        N = 7

    ''' Remove all contents in output directory first '''
    files = sorted(glob.glob(opath + basename + '*.nc'))
    for f in files:
        os.remove(f)

    ''' Process HINDCAST first '''
    files = sorted(glob.glob(hcpath + '**/' + basename + '*.nc')) # Get list of hindcast files
    for f in files:
        # Get date from file name
        date_i = datetime.strptime(os.path.basename(f).replace(basename, '').replace('.nc', ''), '%Y%m%d')
        # If date is within the desired time range, copy to aggregated directory 
        if date_i >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=N):
            shutil.copyfile(f, opath + os.path.basename(f)); print(os.path.basename(f))

    ''' Then process FORECAST '''
    files = sorted(glob.glob(fcpath +  basename + '*.nc')) # Get list of forecast files
    for f in files:
        if os.path.isfile(opath + os.path.basename(f)): # Check if file already exists from hindcast
            # Get file size of forecast file
            fcsize = Path(f).stat().st_size
            # Get file size of hindcast file
            hcsize = Path(opath + os.path.basename(f)).stat().st_size 

            if fcsize > 20*hcsize:
                # This is the last historical hindcast file, which just contains one time record at 00:00
                # In this case, and ONLY in this case, we replace the hindcast with the forecast
                shutil.copyfile(f, opath + os.path.basename(f)); print(os.path.basename(f))
            else:
                continue

        # Get date from file name
        date_i = datetime.strptime(os.path.basename(f).replace(basename, '').replace('.nc', ''), '%Y%m%d')
        # If date is within the desired time range, copy to aggregated directory 
        if date_i >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=N):
            shutil.copyfile(f, opath + os.path.basename(f)); print(os.path.basename(f))

if __name__ == '__main__':
    main()
