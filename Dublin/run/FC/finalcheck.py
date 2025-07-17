from netCDF4 import Dataset, num2date
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import glob

from log import set_logger, now
import traceback
import argparse

msg = '''Given a BASENAME (-b) (e.g. "DUBLIN_"), an absolute PATH (-p) and baseline REFERENCE (-r) for CROCO time (e.g. "19680523"), this 
         function produces time series plots of sea level, temperature and salinity to be sent by email to administrator. This is to check
         that the hindcast+forecast ran properly. '''

logger = set_logger()

def to_datetime(inp):
    return np.array([datetime(i.year, i.month, i.day, i.hour, i.minute, 0) for i in inp])

def check_history(path, basename, units, lat, lon):
    ''' Process history ''' 
    
    # Get list of STATIONS files
    files = sorted(glob.glob((path + basename + '*.nc')))
    
    # Read stations coordinates from first file
    with Dataset(files[0], 'r') as nc:
        # Read longitude
        lonp = nc.variables['lon_rho'][0,:]
        # Read latitude
        latp = nc.variables['lat_rho'][:,0]
    
    # Find nearest station to requested site
    wx = np.argmin(abs(lonp - lon))
    wy = np.argmin(abs(latp - lat))
  
    # Output initialization 
    time, zeta, temp, salt, R = np.empty(()), np.empty(()), np.empty(()), np.empty(()), np.empty(())
    # Loop along files
    for f in files:
        with Dataset(f, 'r') as nc:            
            # Read time
            t = num2date(nc.variables['time'][:], units)
            # Append
            time = np.append(time, t)
            
            # Get CROCO CPP options of this file
            CPP = nc.getncattr('CPP-options')
            if basename + 'HC' in CPP:
                r = np.ones_like(t)  # Hindcast
            elif basename + 'FC' in CPP:
                r = np.zeros_like(t) # Forecast
            # Append
            R = np.append(R, r)
            
            # Read sea level
            z = nc.variables['zeta'][:,wy,wx]
            # Append
            zeta = np.append(zeta, z)
            
            # Read temperature
            T = nc.variables['temp'][:,-1,wy,wx]
            # Append
            temp = np.append(temp, T)
            
            # Read salinity
            S = nc.variables['salt'][:,-1,wy,wx]
            # Append
            salt = np.append(salt, S)
                    
    time, zeta, temp, salt, R = to_datetime(time[1:]), zeta[1:], temp[1:], salt[1:], R[1:]
    
    ''' Plot '''
    fig, ax = plt.subplots(1)
    # Plot time series    
    plt.plot(time[R==1], zeta[R==1]-zeta.mean(), label='HC')    
    plt.plot(time[R==0], zeta[R==0]-zeta.mean(), label='FC')
    # Rotate datetime x-axis tick labels
    plt.xticks(rotation=30, ha='right')
    # Add grid
    plt.grid(visible='on')
    # Add y-axis label
    plt.ylabel('m')
    # Set x-axis limits
    plt.xlim([time[0], time[-1]])
    # Add title
    plt.title(f'HISTORY: Sea level at {lat:.3f}, {lon:.3f}')   
    # Add legend
    plt.legend()
    # Save and close
    plt.tight_layout(); plt.savefig('HIS-zeta.png', dpi=300); plt.close()
    
    fig, ax = plt.subplots(1)
    # Plot time series    
    plt.plot(time[R==1], temp[R==1], label='HC')    
    plt.plot(time[R==0], temp[R==0], label='FC')    
    # Rotate datetime x-axis tick labels
    plt.xticks(rotation=30, ha='right')
    # Add grid
    plt.grid(visible='on')
    # Add y-axis label
    plt.ylabel(r'$\degree$C')
    # Set x-axis limits
    plt.xlim([time[0], time[-1]])
    # Add title
    plt.title(f'HISTORY: Temperature at {lat:.3f}, {lon:.3f}')  
    # Add legend
    plt.legend()
    # Save and close
    plt.tight_layout(); plt.savefig('HIS-temp.png', dpi=300); plt.close()
    
    fig, ax = plt.subplots(1)
    # Plot time series    
    plt.plot(time[R==1], salt[R==1], label='HC')    
    plt.plot(time[R==0], salt[R==0], label='FC')
    # Rotate datetime x-axis tick labels
    plt.xticks(rotation=30, ha='right')
    # Add grid
    plt.grid(visible='on')    
    # Set x-axis limits
    plt.xlim([time[0], time[-1]])
    # Add title
    plt.title(f'HISTORY: Salinity at {lat:.3f}, {lon:.3f}') 
    # Add legend
    plt.legend()
    # Save and close
    plt.tight_layout(); plt.savefig('HIS-salt.png', dpi=300); plt.close()
    
def check_averages(path, basename, units, lat, lon):
    ''' Process averages ''' 
    
    # Get list of STATIONS files
    files = sorted(glob.glob((path + basename + '*.nc')))
    
    # Read stations coordinates from first file
    with Dataset(files[0], 'r') as nc:
        # Read longitude
        lonp = nc.variables['lon_rho'][0,:]
        # Read latitude
        latp = nc.variables['lat_rho'][:,0]
    
    # Find nearest station to requested site
    wx = np.argmin(abs(lonp - lon))
    wy = np.argmin(abs(latp - lat))
  
    # Output initialization 
    time, zeta, temp, salt, R = np.empty(()), np.empty(()), np.empty(()), np.empty(()), np.empty(())
    # Loop along files
    for f in files:
        with Dataset(f, 'r') as nc:            
            # Read time
            t = num2date(nc.variables['time'][:], units)
            # Append
            time = np.append(time, t)
            
            # Get CROCO CPP options of this file
            CPP = nc.getncattr('CPP-options')
            if basename + 'HC' in CPP:
                r = np.ones_like(t)  # Hindcast
            elif basename + 'FC' in CPP:
                r = np.zeros_like(t) # Forecast
            # Append
            R = np.append(R, r)
            
            # Read chlorophyll
            z = nc.variables['DCHL'][:,-1,wy,wx]
            # Append
            zeta = np.append(zeta, z)
            
            # Read temperature
            T = nc.variables['temp'][:,-1,wy,wx]
            # Append
            temp = np.append(temp, T)
            
            # Read salinity
            S = nc.variables['salt'][:,-1,wy,wx]
            # Append
            salt = np.append(salt, S)
                    
    time, zeta, temp, salt, R = to_datetime(time[1:]), zeta[1:], temp[1:], salt[1:], R[1:]
    
    ''' Plot '''
    fig, ax = plt.subplots(1)
    # Plot time series    
    plt.plot(time[R==1], zeta[R==1], label='HC')    
    plt.plot(time[R==0], zeta[R==0], label='FC')
    # Rotate datetime x-axis tick labels
    plt.xticks(rotation=30, ha='right')
    # Add grid
    plt.grid(visible='on')
    # Add y-axis label
    plt.ylabel(r'mg $m^-3$')
    # Set x-axis limits
    plt.xlim([time[0], time[-1]])
    # Add title
    plt.title(f'AVERAGES: Diatoms chlorophyll at {lat:.3f}, {lon:.3f}')   
    # Add legend
    plt.legend()
    # Save and close
    plt.tight_layout(); plt.savefig('AVG-chl.png', dpi=300); plt.close()
    
    fig, ax = plt.subplots(1)
    # Plot time series    
    plt.plot(time[R==1], temp[R==1], label='HC')    
    plt.plot(time[R==0], temp[R==0], label='FC')    
    # Rotate datetime x-axis tick labels
    plt.xticks(rotation=30, ha='right')
    # Add grid
    plt.grid(visible='on')
    # Add y-axis label
    plt.ylabel(r'$\degree$C')
    # Set x-axis limits
    plt.xlim([time[0], time[-1]])
    # Add title
    plt.title(f'AVERAGES: Temperature at {lat:.3f}, {lon:.3f}')  
    # Add legend
    plt.legend()
    # Save and close
    plt.tight_layout(); plt.savefig('AVG-temp.png', dpi=300); plt.close()
    
    fig, ax = plt.subplots(1)
    # Plot time series    
    plt.plot(time[R==1], salt[R==1], label='HC')    
    plt.plot(time[R==0], salt[R==0], label='FC')
    # Rotate datetime x-axis tick labels
    plt.xticks(rotation=30, ha='right')
    # Add grid
    plt.grid(visible='on')    
    # Set x-axis limits
    plt.xlim([time[0], time[-1]])
    # Add title
    plt.title(f'AVERAGES: Salinity at {lat:.3f}, {lon:.3f}') 
    # Add legend
    plt.legend()
    # Save and close
    plt.tight_layout(); plt.savefig('AVG-salt.png', dpi=300); plt.close()
    

def main():
    ''' This script carries out final checks to make sure model run was good.
    It plots time series of sea level and temperature. These plots are sent by
    email to administrator '''
    
    # Initialize argument parser
    parser = argparse.ArgumentParser(description=msg)
    # Define command-line arguments
    parser.add_argument('-b', '--Basename', help='Prefix for output, archived CROCO files')
    parser.add_argument('-p', '--Path', help='Output path for CROCO files')
    parser.add_argument('-r', '--Reference', help='Reference baseline for time used in CROCO')
    parser.add_argument('-x', '--Longitude', help='Longitude to extract data from')
    parser.add_argument('-y', '--Latitude', help='Latitude to extract data from')

    # Read arguments from command line
    args = parser.parse_args()
    if args.Basename:
        basename = args.Basename
    else:
        return

    if args.Path:
        path = args.Path + '/'
    else:
        return

    if args.Reference:
        offset = datetime.strptime(args.Reference, '%Y%m%d')
    else:
        return

    units = 'seconds since ' + offset.strftime('%Y-%m-%d')

    if args.Longitude:
        lon = float(args.Longitude)
    else:
        return

    if args.Latitude:
        lat = float(args.Latitude)
    else:
        return
    
    if 'AVERAGES' in path:
        check_averages(path, basename, units, lat, lon)
    elif 'HISTORY' in path:
        check_history(path, basename, units, lat, lon)
    
if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error("Exception while running HC+FC Final Check: ")
        logger.error(traceback.format_exc())
