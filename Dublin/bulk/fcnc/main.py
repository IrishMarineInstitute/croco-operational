from datetime import date, datetime, timedelta
from create_bulk import create_bulk
from ecmwf2croco import ecmwf2croco
from os.path import basename
from netCDF4 import Dataset
import numpy as np
import traceback
import os

from log import set_logger, now

logger = set_logger()

def to_datetime(date):
    ''' Converts a numpy datetime64 to a Python datetime '''

    timestamp = ((date - np.datetime64('1970-01-01T00:00:00'))
                 / np.timedelta64(1, 's'))
    return datetime.utcfromtimestamp(timestamp)

def configuration():
    ''' Read configuration file '''
    config = {}
    with open('config', 'r') as f:
        for line in f:
            if line.strip() and line[0] != '!': # Exclude comments and blank lines
                # Ignore comments at the end of line
                line = line.split('!')[0] 
                # Split. Fist word is a keyword
                out = line.split(); key = out[0]; val = out[1:]                                             
                if len(val) == 1: # This is for sigle-valued keywords
                    config[key] = val[0]
                else: # This is for multiple-valued keywords
                    config[key] = val
    return config

def get_ECMWF_grid(config):
    ''' Get ECMWF grid domain and resolution '''

    # Western and eastern boundaries [degrees east]
    w, e = float(config.get('ECMWF_W')), float(config.get('ECMWF_E'))
    # Southern and northern boundaries [degrees north]
    s, n = float(config.get('ECMWF_S')), float(config.get('ECMWF_N'))

    # Grid resolution [deg]
    D = float(config.get('ECMWF_DH'))

    return np.arange(w, e+D, D), np.arange(s, n+D, D) # Return ECMWF grid

def make_bulk():
    ''' Create CROCO ECMWF bulk forcing files '''

    config = configuration()

    ''' Setting time '''
    # Set start time for FC bulk forcing. Extend it to yesterday 00:00 AM for the forecast catch-up run
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    # Set end time for FC bulk forcing
    end = today + timedelta(days=int(config.get('days-ahead'))+2)

    # Time list for bulk forcing 
    DateTime = np.arange(today, end, timedelta(hours=1))
    DateTime = np.array([to_datetime(i) for i in DateTime])
    # Get CROCO refence time
    offset = datetime.strptime(config.get('offset'), '%Y%m%d')
    # Convert to days since offset
    time = np.array([(i - offset).total_seconds()/86400 for i in DateTime])

    # Set output directory to save NetCDF files
    metpath = config.get('metpath')

    ''' Set ECMWF grid (defined in configuration) '''
    lon, lat = get_ECMWF_grid(config)

    ''' Process Hindcast '''
    forecastPath = metpath + 'FC/'
    # Set path for input NetCDF files
    ncPathIn = forecastPath + 'NETCDF/' 
    # Set path for output NetCDF files
    ncPathOut = ncPathIn + today.strftime('%Y%m%d') + '/'
    if not os.path.isdir(ncPathOut):
        os.makedirs(ncPathOut)

    ''' Setting output NetCDF file names '''
    datestring = today.strftime('%Y%m%d')
    fwind = ncPathOut + 'ECMWF_frc_wind_' + datestring + '.nc' # Wind
    fflux = ncPathOut + 'ECMWF_frc_hf_'   + datestring + '.nc' # Radiation
    faire = ncPathOut + 'ECMWF_frc_air_'  + datestring + '.nc' # T, P, Q, rain

    ''' Create forcing files '''
    # Get dimensions
    L, M, T = len(lon), len(lat),len(time)
    # Create NetCDF files
    logger.info(f'{now()} Creating {basename(faire)}, {basename(fflux)}, {basename(fwind)}')
    create_bulk(faire, fflux, fwind, L, M, T, offset, lon, lat, time)

    ''' Set ECMWF variable names '''
    air, flx, wnd = ('Pair', 'Tair', 'Qair', 'cloud', 'rain'), ('swrad', 'lwrad', 'lwrad_down'), ('Uwind', 'Vwind')

    ''' MAIN LOOP '''
    logger.info(' '); logger.info(f'{now()} Starting writing loop...')
    for w, (i, j) in enumerate(zip(time, DateTime)):
        logger.info(f'{now()}   Writing {j.strftime("%Y%m%d %H:%M")}')
        for v in air:
            write_ecmwf(ncPathIn, faire, i, j, v, 'air_', w)
        for v in flx:
            write_ecmwf(ncPathIn, fflux, i, j, v, 'hf_', w)
        for v in wnd:
            write_ecmwf(ncPathIn, fwind, i, j, v, 'wind_', w)

    ''' Convert to CROCO format '''
    # CROCO online interpolation bulk forcing files follow certain conventions. 
    # Files must be produced for each month and parameter separately. If the
    # simulation spans multiple months, a separate file must be created for each
    # month. So, let's first determine the start and end month of this run.
    iYear, iMonth, eYear, eMonth = today.year, today.month, end.year, end.month

    if os.path.isfile('/log/bulk-fcnc-abspath.config'):
        os.remove('/log/bulk-fcnc-abspath.config')
    if os.path.isfile('/log/bulk-fcnc-basename.config'):
        os.remove('/log/bulk-fcnc-basename.config')

    # Process start month
    ecmwf2croco(faire, fflux, fwind, iYear, iMonth)

    if eMonth != iMonth:
        ecmwf2croco(faire, fflux, fwind, eYear, eMonth)  # Process end month


def write_ecmwf(path, file, time, DateTime, variable, namestr, index):

    if namestr == 'air_':
        t = 'pair_time' # Name of NetCDF time variable in air files
    elif namestr == 'hf_':
        t = 'srf_time'  # Name of NetCDF time variable in flux files
    elif namestr == 'wind_':
        t = 'wind_time' # Name of NetCDF time variable in wind files
    
    inFile = path + 'ECMWF_' + namestr + DateTime.strftime('%Y%m%d') + '.nc'
    if not os.path.isfile(inFile):
        raise FileNotFoundError(f'FATAL: Input file {inFile} is missing!'); return

    with Dataset(inFile, 'r') as nc:
        inTime = nc.variables[t][:]
        # Find the required time index for this iteration
        i = np.argmin(abs(inTime - time))
        if abs(inTime[i] - time) > 1e-6:
            raise IndexError(f'FATAL: {time} not found in {inFile}')

        # Read data
        data = nc.variables[variable][i, :, :]
        # Write data
        with Dataset(file, 'a') as cdf:
            cdf.variables[variable][index, :, :] = data

if __name__ == '__main__':
    try: 
        make_bulk()
    except Exception as e:
        logger.error("Exception while creating FC atmospheric forcing files: " + str(e.args[0]))
        logger.error(traceback.format_exc())
