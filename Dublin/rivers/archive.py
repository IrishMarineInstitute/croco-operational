from datetime import datetime, timedelta
from netCDF4 import Dataset
from math import floor
import numpy as np
import os

def time_river_archive(config):
    ''' Set time of river archive '''

    # Get CROCO offset time
    offset = datetime.strptime(config.get('offset'), '%Y%m%d')

    # Start date for archive
    idate = datetime.strptime(config.get('idateArchive'), '%Y%m%d')

    # End date for archive
    edate = datetime.strptime(config.get('edateArchive'), '%Y%m%d')

    # Time step
    DT = timedelta(minutes=15)

    # Make sure time is an array of datetime objects
    time = np.append(np.arange(idate, edate, DT),
            datetime.combine(edate, datetime.min.time()))
    time = np.array([(i - offset).total_seconds()/86400 for i in time])

    return time, offset

def create_river_archive(config, name):
    ''' Create river archive file '''

    time, offset = time_river_archive(config); T = len(time)

    # Path of river archive
    path = config.get('archivepath') + '/' 

    filename = f'{path}{name}.nc'

    with Dataset(filename, 'w', format='NETCDF4') as nc:

        ''' Create dimensions '''
        nc.createDimension('time', T)

        ''' Create variables '''
        t = nc.createVariable('time', 'f8', dimensions=('time'))
        t.standard_name = 'time'
        t.units = 'days since ' + offset.strftime('%Y-%m-%d')
        t[:] = time

        flow = nc.createVariable('flow', 'f8', dimensions=('time'))
        flow.standard_name = 'water_volume_transport_into_sea_water_from_rivers'
        flow.units = 'm3 s-1'

        temp = nc.createVariable('temperature', 'f8', dimensions=('time'))
        temp.standard_name = 'river_water_temperature'
        temp.units = 'Celsius'

def update_river_archive(config, name, time, flow, temp):
    ''' Update river archive '''

    offset = datetime.strptime(config.get('offset'), '%Y%m%d')

    try:
        today = datetime.strptime(config.get('mydate'), '%Y%m%d')
    except ValueError:
        today = datetime.now()

    today = floor((today - offset).total_seconds()/86400)

    # Path of river archive
    path = config.get('archivepath') + '/' 
    if not os.path.isdir(path):
        os.makedirs(path)

    filename = f'{path}{name}.nc'
    if not os.path.isfile(filename):
        create_river_archive(config, name)

    with Dataset(filename, 'a') as nc:
        # Read time
        t = nc.variables['time'][:]

        for i, Q, T in zip(time, flow, temp):
            if i > today:
                break # Avoid writing forecast extrapolations into archive
            w = np.argmin(abs(t - i)) # Nearest time index in archive
            # Write flow
            nc.variables['flow'][w] = Q
            # Write temperature
            nc.variables['temperature'][w] = T
