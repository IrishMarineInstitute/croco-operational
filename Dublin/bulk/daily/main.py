from datetime import date, datetime, timedelta
from create_bulk import create_bulk
from write_bulk import write_bulk, to_datetime
from os.path import basename
import numpy as np
import traceback
import glob
import time
import os

from log import set_logger, now

logger = set_logger()

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
    # Set start time for bulk forcing (last midnight)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # Yesterday date is also needed to retrieve the name of some GRIB files
    yesterday = today - timedelta(days=1)
    # First, set up some useful date strings
    yearYesterday = yesterday.strftime('%Y')
    dateYesterday = yesterday.strftime('%m%d')
    yearToday = today.strftime('%Y')
    dateToday = today.strftime('%m%d')

    # Time list for bulk forcing (24 hours, hourly)
    time = np.arange(today, today+timedelta(days=1), timedelta(hours=1))
    # Get CROCO refence time
    offset = datetime.strptime(config.get('offset'), '%Y%m%d')
    # Convert to days since offset
    time = np.array([(to_datetime(i) - offset).total_seconds()/86400 for i in time])

    # Set output directory to save NetCDF files
    metpath = config.get('metpath')

    ''' Set ECMWF grid (defined in configuration) '''
    lon, lat = get_ECMWF_grid(config)

    ''' Process Hindcast '''
    hindcastPath = metpath + 'HC/'; logger.info(f'{now()} Creating ECMWF HC files...')
    # Remove NetCDF files older than 10 days
    clean(hindcastPath, 10)
    # Set path for NetCDF files
    ncPath = hindcastPath + 'NETCDF/' + today.strftime('%Y') + '/'
    if not os.path.isdir(ncPath):
        os.makedirs(ncPath)

    ''' Setting output NetCDF file names '''
    datestring = today.strftime('%Y%m%d')
    fwind = ncPath + 'ECMWF_wind_' + datestring + '.nc' # Wind
    fflux = ncPath + 'ECMWF_hf_'   + datestring + '.nc' # Radiation
    faire = ncPath + 'ECMWF_air_'  + datestring + '.nc' # T, P, Q, rain

    ''' Create forcing files '''
    # Get dimensions
    L, M, T = len(lon), len(lat),len(time)
    # Create NetCDF files
    logger.info(f'{now()} Creating {basename(faire)}, {basename(fflux)}, {basename(fwind)}...')
    create_bulk(faire, fflux, fwind, L, M, T, offset, lon, lat, time)

    gribPath = hindcastPath + 'GRIB/' + yearYesterday + '/'
    grib1 = gribPath + 'IQS' + yearYesterday + dateYesterday + '1200' + dateToday     + '00001'
    grib2 = gribPath + 'IQS' + yearYesterday + dateYesterday + '1200' + dateYesterday + '23001'

    eflag = write_bulk(faire, fflux, fwind, today, 0, grib1, grib2=grib2)
    if eflag:
        logger.error("Exception while creating HC atmospheric forcing files at index 0")

    gribPath = hindcastPath + 'GRIB/' + yearToday + '/'
    for i in range(1, 24):
        time_i = today + timedelta(hours=i); str1 = time_i.strftime('%m%d%H')
        logger.info(f'{now()}     {str1}')
        # Previous file
        time_0 = today + timedelta(hours=i-1); str0 = time_0.strftime('%m%d%H')

        if i < 13:
            grib1 = 'IQS' + yearToday + dateToday + '0000' + str1 + '001'
            grib2 = 'IQS' + yearToday + dateToday + '0000' + str0 + '001'
        else:
            grib1 = 'IQS' + yearToday + dateToday + '1200' + str1 + '001'
            grib2 = 'IQS' + yearToday + dateToday + '1200' + str0 + '001'

        grib1 = gribPath + grib1
        if ( i == 1 ) or ( i == 13 ):
            grib2 = ''
        else:
            grib2 = gribPath + grib2

        eflag = write_bulk(faire, fflux, fwind, time_i, i, grib1, grib2=grib2)
        if eflag:
            logger.error(f"Exception while creating HC atmospheric forcing files at index {i}")

    logger.info(' ')

    ''' Process forecast '''
    forecastPath = metpath + 'FC/'; logger.info(f'{now()} Creating ECMWF FC files...')
    # Remove NetCDF files older than 3 days
    clean(forecastPath, 3)
    # Set path for NetCDF files
    ncPath = forecastPath + 'NETCDF/'
    if not os.path.isdir(ncPath):
        os.makedirs(ncPath)

    # Set start time for bulk forcing 
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    # Yesterday date is also needed to retrieve the name of some GRIB files
    yesterday = today - timedelta(days=1)
    # First, set up some useful date strings
    yearYesterday = yesterday.strftime('%Y')
    dateYesterday = yesterday.strftime('%m%d')
    yearToday = today.strftime('%Y')
    dateToday = today.strftime('%m%d')

    # Time list for bulk forcing (24 hours, hourly)
    time = np.arange(today, today+timedelta(days=4), timedelta(hours=1))
    # Convert to days since offset
    time = np.array([(to_datetime(i) - offset).total_seconds()/86400 for i in time])

    gribPath = forecastPath + 'GRIB/'
    # Define alternative path in case some file cannot be found
    #gribPath2 = hindcastPath + 'GRIB/' + yearToday + '/'
    #gribPath3 = hindcastPath + 'GRIB/' + yearYesterday + '/'
    for i in range(4):
        time_i = today + timedelta(days=i)

        ''' Setting output NetCDF file names '''
        datestring = time_i.strftime('%Y%m%d')
        fwind = ncPath + 'ECMWF_wind_' + datestring + '.nc' # Wind
        fflux = ncPath + 'ECMWF_hf_'   + datestring + '.nc' # Radiation
        faire = ncPath + 'ECMWF_air_'  + datestring + '.nc' # T, P, Q, rain

        logger.info(f'{now()} Creating {basename(faire)}, {basename(fflux)}, {basename(fwind)}...')
        create_bulk(faire, fflux, fwind, L, M, 24, 
             offset, lon, lat, time[24*i:24*(i+1)])

        if i == 3:
            for k in range(7):
                time_k = time_i + timedelta(hours=k); str1 = time_k.strftime('%m%d%H')
                logger.info(f'{now()}     {str1}')
                # Previous file
                time_0 = time_i + timedelta(hours=k-1); str0 = time_0.strftime('%m%d%H')
                
                grib1 = gribPath + 'IQS' + yearYesterday + dateYesterday + '1200' + str1 + '001'
                #if not os.path.isfile(grib1):
                #    grib1 = gribPath2 + 'IQS' + yearYesterday + dateYesterday + '1200' + str1 + '001'
                #    if not os.path.isfile(grib1):
                #        grib1 = gribPath3 + 'IQS' + yearYesterday + dateYesterday + '1200' + str1 + '001'

                grib2 = gribPath + 'IQS' + yearYesterday + dateYesterday + '1200' + str0 + '001'
                #if not os.path.isfile(grib2):
                #    grib2 = gribPath2 + 'IQS' + yearYesterday + dateYesterday + '1200' + str0 + '001'
                #    if not os.path.isfile(grib2):
                #        grib2 = gribPath3 + 'IQS' + yearYesterday + dateYesterday + '1200' + str0 + '001'

                eflag = write_bulk(faire, fflux, fwind, time_k, k, grib1, grib2=grib2)
                if eflag:
                    logger.error(f"Exception while creating FC atmospheric forcing files at index {k}")

            k = 12; # 1200 value from IQD file

            time_k = time_i + timedelta(hours=k); str1 = time_k.strftime('%m%d%H')
            logger.info(f'{now()}     {str1}')
            # Get full path of IQD file
            grib1 = gribPath + 'IQD' + yearYesterday + dateYesterday + '1200' + str1 + '001'
            #if not os.path.isfile(grib1):
            #    grib1 = gribPath2 + 'IQD' + yearYesterday + dateYesterday + '1200' + str1 + '001'
            #    if not os.path.isfile(grib1):
            #        grib1 = gribPath3 + 'IQD' + yearYesterday + dateYesterday + '1200' + str1 + '001'

            # Write into NetCDF
            eflag = write_bulk(faire, fflux, fwind, time_k, k, grib1)
            if eflag:
                logger.error(f"Exception while creating FC atmospheric forcing files at index {k}")

        else:
            for k in range(24):
                time_k = time_i + timedelta(hours=k); str1 = time_k.strftime('%m%d%H')
                logger.info(f'{now()}     {str1}')
                # Previous file
                time_0 = time_i + timedelta(hours=k-1); str0 = time_0.strftime('%m%d%H')
                
                grib1 = gribPath + 'IQS' + yearYesterday + dateYesterday + '1200' + str1 + '001'
                #if not os.path.isfile(grib1):
                #    grib1 = gribPath2 + 'IQS' + yearYesterday + dateYesterday + '1200' + str1 + '001'
                #    if not os.path.isfile(grib1):
                #        grib1 = gribPath3 + 'IQS' + yearYesterday + dateYesterday + '1200' + str1 + '001'

                grib2 = gribPath + 'IQS' + yearYesterday + dateYesterday + '1200' + str0 + '001'
                #if not os.path.isfile(grib2):
                #    grib2 = gribPath2 + 'IQS' + yearYesterday + dateYesterday + '1200' + str0 + '001'
                #    if not os.path.isfile(grib2):
                #        grib2 = gribPath3 + 'IQS' + yearYesterday + dateYesterday + '1200' + str0 + '001'

                eflag = write_bulk(faire, fflux, fwind, time_k, k, grib1, grib2=grib2)
                if eflag:
                    logger.error(f"Exception while creating FC atmospheric forcing files at index {k}")

    logger.info(' '); logger.info(f'{now()} Finished creating ECMWF ROMS forcing files')

def clean(path, D):
    ''' Removes files in path older than D days '''
    old = time.time() - D * 86400
    for f in glob.glob(path + '**/*.nc', recursive=True):
        file = os.path.abspath(f)
        if os.path.getctime(file) < old:
            logger.info(f'{now()} Deleting {file}') 
            os.remove(file)

if __name__ == '__main__':
    try: 
        make_bulk()
    except Exception as e:
        logger.error("Exception while creating daily atmospheric forcing files: " + str(e.args[0]))
        logger.error(traceback.format_exc())
