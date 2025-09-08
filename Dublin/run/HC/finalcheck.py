from netCDF4 import Dataset, num2date
from datetime import datetime
import matplotlib.pyplot as plt
from log import set_logger, now
import numpy as np
import traceback
import argparse
import wget
import glob
import os

msg = '''Given a BASENAME (-b) (e.g. "DUBLIN_"), an absolute PATH (-p) and baseline REFERENCE (-r) for CROCO time (e.g. "19680523"), this 
         function produces time series plots of sea level, temperature and salinity to be sent by email to administrator. This is to check
         that the hindcast ran properly. '''

logger = set_logger()

def get_tide_gauges():
    
    return {
        'Aranmore Island - Leagbarrow' :  1,
        'Ballycotton Harbour':            2,
        'Ballyglass Harbour':             3,
        'Buncranna':                      4,
        'Castletownbere Port':            5,
        'Dingle Harbour':                 6,
        'Dublin Port':                    7,
        'Dunmore East Harbour':           8,
        'Galway Port':                    9,
        'Galway Port 2':                 10,
        'Howth Water Level 1':           11,
        'Howth Water Level 2':           12,
        'Inishmore':                     13,
        'Killybegs Port':                14,
        'Kilrush Lough':                 15,
        'Kinvara - Unreferenced':        16,
        'Malin Head - Portmore Pier':    17,
        'Roonagh Pier':                  18,
        'Rosslare':                      19,
        'Skerries Harbour':              20,
        'Sligo':                         21,
        'Union Hall Harbor':             22,
        'Union Hall Harbor 2':           23,
        'Wexford Harbour':               24
            }

def erddap(idate, edate, station):
    ''' Download data from ERDDAP '''
               
    url = "https://erddap.marine.ie/erddap/tabledap/IrishNationalTideGaugeNetwork.nc?" + "time%2Clatitude%2Clongitude%2CWater_Level_OD_Malin&time%3E=" + idate + "T00%3A00%3A00Z&time%3C=" + edate + "T00%3A00%3A00Z&station_id=%22" + station.replace(' ', '%20') + '%22'
 
    f = wget.download(url)
        
    # Open file 
    with Dataset(f, 'r') as nc:       
        # Read tide gauge longitude
        lon = np.unique(nc.variables['longitude'][:])[0]
        # Read tide gauge latitude
        lat = np.unique(nc.variables['latitude'][:])[0]
        # Read time
        time = num2date(nc.variables['time'][:],
                nc.variables['time'].units)
        # Read sea level
        ssh = nc.variables['Water_Level_OD_Malin'][:]
        
    time = np.array([datetime(i.year, i.month, i.day, i.hour, i.minute, i.second) 
                     for i in time]) # Convert to datetime
        
    os.remove(f) 
    
    return lon, lat, time, ssh

def to_datetime(inp):
    return np.array([datetime(i.year, i.month, i.day, i.hour, i.minute, 0) for i in inp])

def check_stations(path, basename, units, lat, lon):
    ''' Process stations ''' 
    
    # Get list of STATIONS files
    files = sorted(glob.glob((path + basename + 'STN_*.nc')))
    
    # Read stations coordinates from first file
    with Dataset(files[0], 'r') as nc:
        # Read longitude
        lonp = nc.variables['lon'][:]
        # Read latitude
        latp = nc.variables['lat'][:]
    
    # Find nearest station to requested site
    wx = np.argmin(abs(lonp - lon))
    wy = np.argmin(abs(latp - lat))
    
    # Make sure indexes for latitude and longitude are both the same
    assert(wx == wy)

    # Output initialization 
    time, zeta, temp, salt = np.empty(()), np.empty(()), np.empty(()), np.empty(())
    # Loop along files
    for f in files:
        with Dataset(f, 'r') as nc:
            # Read time
            t = num2date(nc.variables['scrum_time'][:], units)
            # Append
            time = np.append(time, t)
            
            # Read sea level
            z = nc.variables['zeta'][:, wx]
            # Append
            zeta = np.append(zeta, z)
            
            # Read temperature
            T = nc.variables['temp'][:,wx,-1]
            # Append
            temp = np.append(temp, T)
            
            # Read salinity
            S = nc.variables['salt'][:,wx,-1]
            # Append
            salt = np.append(salt, S)
                    
    time, zeta, temp, salt = to_datetime(time[1:]), zeta[1:], temp[1:], salt[1:]
    
    temp[temp > 100] = np.nan
    salt[salt > 100] = np.nan
    
    ''' Download observed sea level from tide gauge '''
    station = 11 
    # Get name of tide gauge station
    tideDict = get_tide_gauges()    
    for key, val in tideDict.items():
        if val == station:
            GaugeName = key
    _, _, GaugeTime, GaugeLevel = erddap(time[0].strftime('%Y-%m-%d'), 
                                             time[-1].strftime('%Y-%m-%d'), 
                                             GaugeName)
    
    ''' Plot '''
    fig, ax = plt.subplots(1)
    # Plot time series
    plt.plot(GaugeTime, GaugeLevel-GaugeLevel.mean(), label='Gauge')
    plt.plot(time, zeta-zeta.mean(), label='CROCO')    
    # Rotate datetime x-axis tick labels
    plt.xticks(rotation=30, ha='right')
    # Add grid
    plt.grid(visible='on')
    # Add y-axis label
    plt.ylabel('m')
    # Set x-axis limits
    plt.xlim([time[0], time[-1]])
    # Add title
    plt.title(f'STATIONS: Sea level at {lat:.3f}, {lon:.3f}')
    # Add legend
    ax.legend()
    # Save and close
    plt.tight_layout(); plt.savefig('ST-zeta.png', dpi=300); plt.close()
    
    fig, ax = plt.subplots(1)
    # Plot time series    
    plt.plot(time, temp)    
    # Rotate datetime x-axis tick labels
    plt.xticks(rotation=30, ha='right')
    # Add grid
    plt.grid(visible='on')
    # Add y-axis label
    plt.ylabel(r'$\degree$C')
    # Set x-axis limits
    plt.xlim([time[0], time[-1]])
    # Add title
    plt.title(f'STATIONS: Temperature at {lat:.3f}, {lon:.3f}')  
    # Save and close
    plt.tight_layout(); plt.savefig('ST-temp.png', dpi=300); plt.close()
    
    fig, ax = plt.subplots(1)
    # Plot time series    
    plt.plot(time, salt)    
    # Rotate datetime x-axis tick labels
    plt.xticks(rotation=30, ha='right')
    # Add grid
    plt.grid(visible='on')    
    # Set x-axis limits
    plt.xlim([time[0], time[-1]])
    # Add title
    plt.title(f'STATIONS: Salinity at {lat:.3f}, {lon:.3f}')    
    # Save and close
    plt.tight_layout(); plt.savefig('ST-salt.png', dpi=300); plt.close()
    
def check_history(path, basename, units, lat, lon):
    ''' Process stations ''' 
    
    # Get list of STATIONS files
    files = sorted(glob.glob((path + basename + 'HIS_*.nc')))
    
    # Read stations coordinates from first file
    with Dataset('croco_grd.nc', 'r') as nc:
        # Read longitude
        lonp = nc.variables['lon_rho'][0,:]
        # Read latitude
        latp = nc.variables['lat_rho'][:,0]
    
    # Find nearest station to requested site
    wx = np.argmin(abs(lonp - lon))
    wy = np.argmin(abs(latp - lat))
  
    # Output initialization 
    time, zeta, temp, salt = np.empty(()), np.empty(()), np.empty(()), np.empty(())
    # Loop along files
    for f in files:
        with Dataset(f, 'r') as nc:
            # Read time
            t = num2date(nc.variables['time'][:], units)
            # Append
            time = np.append(time, t)
            
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
                    
    time, zeta, temp, salt = to_datetime(time[1:]), zeta[1:], temp[1:], salt[1:]
    
    ''' Plot '''
    fig, ax = plt.subplots(1)
    # Plot time series    
    plt.plot(time, zeta-zeta.mean())    
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
    # Save and close
    plt.tight_layout(); plt.savefig('HIS-zeta.png', dpi=300); plt.close()
    
    fig, ax = plt.subplots(1)
    # Plot time series    
    plt.plot(time, temp)    
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
    # Save and close
    plt.tight_layout(); plt.savefig('HIS-temp.png', dpi=300); plt.close()
    
    fig, ax = plt.subplots(1)
    # Plot time series    
    plt.plot(time, salt)    
    # Rotate datetime x-axis tick labels
    plt.xticks(rotation=30, ha='right')
    # Add grid
    plt.grid(visible='on')    
    # Set x-axis limits
    plt.xlim([time[0], time[-1]])
    # Add title
    plt.title(f'HISTORY: Salinity at {lat:.3f}, {lon:.3f}')    
    # Save and close
    plt.tight_layout(); plt.savefig('HIS-salt.png', dpi=300); plt.close()
    

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

    if 'STATIONS' in path:
        check_stations(path, basename, units, lat, lon)
    elif 'HISTORY' in path:
        check_history(path, basename, units, lat, lon)
    
if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error("Exception while running HC Final Check: ")
        logger.error(traceback.format_exc())
