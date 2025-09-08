from create_boundary_file import create_bry
from interpolate_boundary import interpolate_bry_variable 
from total_alkalinity import total_alkalinity
from netCDF4 import Dataset, num2date, date2num
from datetime import date, datetime, timedelta
from log import set_logger, now
import copernicusmarine
import numpy as np
import traceback
import glob
import time
import os

logger = set_logger()

PISCES = ('DIC', 'TALK', 'pH', 'NO3', 'NH4', 'PO4', 'Si', 'O2', 'FER')

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

def get_boundaries(config):
    ''' Get geographical boundaries from configuration file '''
    key, vals = ('west', 'east', 'south', 'north'), []
    for k in key:
        vals.append(float(config.get(k)))
    return vals

def get_dates(config):
    ''' Get dates to process '''

    # Use today as current date, unless selected otherwise
    try:
        today = datetime.strptime(config.get('mydate'), '%Y%m%d')
    except ValueError:
        today = date.today()

    # Get start date to download
    idate = today - timedelta(days=int(config.get('days-back')))
    idatestr = idate.strftime('%Y%m%d')
    # Get end date to download
    edate = today + timedelta(days=int(config.get('days-ahead'))+1)
    edatestr = edate.strftime('%Y%m%d')

    return idate, idatestr, edate, edatestr

def add_offset(filename, offset):
    ''' Read time from a CMEMS NetCDF file and adds an offset (in hours) '''

    with Dataset(filename, 'a') as nc:
        var = nc.variables['time']
        # Get time units
        units = var.units
        # Read time from NetCDF
        time = num2date(var[:], units)
        # Add offset and write into NetCDF
        var[:] = date2num(time + timedelta(hours=offset), units)
       
def copernicus_download(config, dataset, filename, variable, idate, edate):
    ''' Download ocean variable from Copernicus dataset ''' 

    # Get geographical boundaries
    west, east, south, north = get_boundaries(config)

    logger.info(f'{now()} Downloading {dataset}  to {filename}...')
    copernicusmarine.subset(
            username=config.get('username'),
            password=config.get('password'),
            dataset_id=dataset,
            output_directory=config.get('cmemspath'),
            output_filename=filename,
            variables=[variable],
            minimum_longitude=west, maximum_longitude=east,
            minimum_latitude=south, maximum_latitude=north,
            start_datetime=idate.strftime('%Y-%m-%dT00:00:00'),
            end_datetime=edate.strftime('%Y-%m-%dT00:00:00')
            )

def extend_copernicus(f, idate, edate, cdfvar):
    ''' Given a NetCDF file downloaded from CMEMS "f" (absolute path mandatory),
    this function creates an identifical file with the same name (overwrites
    existing file), except that the time dimension is extended to cover the 
    period from IDATE to EDATE (both Python datetime objects). CDFVAR is the
    name of the data variable in the file (e.g. "dissic", "no3", "thetao", etc.)
    
    When the selected time range (IDATE to EDATE) is outside the existing in the
    original NetCDF, it uses the closest data in time to write the data array.
    
    This function is needed to extend biogeochemistry files in CMEMS, which do 
    not cover the full length of the forecast in certain days of the week. As
    a result of this script, an identical NetCDF is created, but with trailing,
    repeated values at the end of the period. '''                                                           

    idate = datetime.combine(idate, datetime.min.time()) # Datetime required
    edate = datetime.combine(edate, datetime.min.time()) # Datetime required

    ''' Create new time array, from IDATE to EDATE '''
    timeList = []
    while idate <= edate:
        timeList.append(idate)
        idate += timedelta(days=1)
    T = len(timeList); timeList = np.array(timeList)
    
    ''' Read file as downloaded from CMEMS '''
    with Dataset(f, 'r') as nc:
        # Read depth
        depth = nc.variables['depth'][:]
        # Read latitude
        latitude = nc.variables['latitude'][:]
        # Read longitude
        longitude = nc.variables['longitude'][:]
        # Read time
        time = nc.variables['time'][:]
        offset = nc.variables['time'].units
        nctime = num2date(time, offset)
        nctime = np.array([datetime(i.year, i.month, i.day) for i in nctime])
        # Read variable
        standard_name = nc.variables[cdfvar].standard_name
        units = nc.variables[cdfvar].units
        data = nc.variables[cdfvar][:]

    if np.array_equal(timeList, nctime):
        return # Time is already as desired. Nothing else needed. Exit
            
    logger.info(f' '); logger.info(f'{now()} Applying time extension to {cdfvar}'); logger.info(f' ')

    # Get dimensions
    _, N, M, L = data.shape
    
    ''' Create output data array '''
    out = np.empty((T, N, M, L))
    # Loop along time to fill output array
    for index, date_i in enumerate(timeList):   
        # Find nearest index
        w = np.argmin(abs(nctime-date_i))
        # Write into output array    
        out[index, :, :, :] = data[w, :, :, :]
        
    ''' Create new NetCDF '''
    if os.path.isfile(f):
        os.remove(f)
    
    with Dataset(f, 'w', format='NETCDF4') as nc:
        nc.createDimension('depth', N)
        nc.createDimension('latitude', M)
        nc.createDimension('longitude', L)
        nc.createDimension('time', T) 
        
        z = nc.createVariable('depth', 'f4', dimensions=('depth',))
        z.standard_name = 'depth'; z.units = 'm'; z[:] = depth
        
        latvar = nc.createVariable('latitude', 'f8', dimensions=('latitude'))
        latvar.standard_name = 'latitude'; latvar.units = 'degrees_north'
        latvar[:] = latitude
        
        lonvar = nc.createVariable('longitude', 'f8', dimensions=('longitude'))
        lonvar.standard_name = 'longitude'; latvar.units = 'degrees_east'
        lonvar[:] = longitude
        
        tvar = nc.createVariable('time', 'f4', dimensions=('time'))
        tvar.standard_name = 'time'; tvar.units = offset
        tvar[:] = date2num(timeList, offset)
        
        datavar = nc.createVariable(cdfvar, 'f8', 
            dimensions=('time', 'depth', 'latitude', 'longitude'))
        datavar.standard_name = standard_name
        datavar.units = units
        datavar[:] = out

def copernicus():
    ''' Download Copernicus datasets for boundary forcing '''

    config = configuration()

    idate, idatestr, edate, edatestr = get_dates(config)

    ''' Set output directory before download '''
    localpath = config.get('cmemspath')
    if not os.path.isdir(localpath):
        logger.info(f'{now()} Creating output directory {localpath}')
        os.makedirs(localpath)
    # Clean directory
    files = glob.glob(f'{localpath}/*.nc')
    for f in files:
        os.remove(f)

    variables = ('zeta', 'u', 'v', 'ubar', 'vbar', 'temp', 'salt',
            'DIC', 'NO3', 'PO4', 'Si', 'O2', 'FER', 'NH4', 'pH')

    for v in variables:
        if v in PISCES and config.get('PISCES') != 'T':
            continue # Ignore PISCES 

        selection = config.get(v) # Get user's choices for this variable

        if selection[0] == 'Y': # 'Yes', download this variable

            dataset = "DATASET-" + str(selection[1]) # CMEMS dataset ID

            try:
                dataset, offset = config.get(dataset)
            except TypeError:
                logger.error(f'{now()} Dataset for {v} not specified'); continue
            except ValueError:
                logger.error(f'{now()} Time offset for {v} not specified for dataset'); continue

            cdfvar = selection[2] # CMEMS ocean variable name
            
            # Set file name to download from Copernicus
            filename = f'cmems-{v}-{idatestr}-{edatestr}.nc'

            # Download using Copernicus Marine API
            copernicus_download(config, dataset, filename, cdfvar, idate, edate)

            if selection[3] == 'T':
                # For this parameter, extend NetCDF to cover the full of the FC period
                extend_copernicus(config.get('cmemspath') + '/' + filename,
                        idate, edate, cdfvar)

            # Add offset time, in hours, to NetCDF time array 
            add_offset(config.get('cmemspath') + '/' + filename, float(offset))

    if config.get('PISCES') == 'T': # PISCES selected
        total_alkalinity(config, idatestr, edatestr) # Calculate total alkalinity

def make_boundary():
    ''' Create CROCO boundary forcing '''

    config = configuration()

    # Get reference offset time for CROCO
    offset = datetime.strptime(config.get('offset'), '%Y%m%d')

    # Get open boundaries
    config['OpenBoundaries'] = [int(i) for i in config.get('obc')]

    # Get directory where Copernicus file should have been already downloaded to
    cmemspath = config.get('cmemspath')

    idate, idatestr, edate, edatestr = get_dates(config)

    # Read time from Copernicus "master" variable, as defined in config
    mastervar = config.get('master')

    filename = f'{cmemspath}/cmems-{mastervar}-{idatestr}-{edatestr}.nc'
    with Dataset(filename, 'r') as nc:
        time = num2date(nc.variables['time'][:],
                nc.variables['time'].units)

    # Make sure time is an array of datetime objects
    time = np.array([datetime(i.year, i.month, i.day, i.hour, i.minute, 0) for i in time])
    # Convert to days since offset time 
    time = np.array([(i - offset).total_seconds()/86400 for i in time])
    # Add time to general setup to define boundary forcing file time dimension
    config['time'] = time # This will be the "master" time array.

    ''' Check if PISCES is activated '''
    if config.get('PISCES') == 'T':
        variables = ('DIC', 'TALK', 'NO3', 'PO4', 'Si', 'O2', 'FER', 'NH4', 'pH')
        for v in variables:
            selection = config.get(v) # Get user's choices for this variable
            if selection[0] == 'Y': # 'Yes', PISCES is used
                # A Copernicus file with this BGC variable should have been downloaded already
                filename = f'{cmemspath}/cmems-{v}-{idatestr}-{edatestr}.nc'
                # Open NetCDF file and read time
                with Dataset(filename, 'r') as nc:
                    time = num2date(nc.variables['time'][:],
                            nc.variables['time'].units)
                # Make sure time is an array of datetime objects
                time = np.array([datetime(i.year, i.month, i.day, i.hour, i.minute, 0) for i in time])
                # Convert to days since offset time 
                time = np.array([(i - offset).total_seconds()/86400 for i in time])
                # Add time to general setup to define boundary forcing file time dimension
                config['pisces-time'] = time # This will be the PISCES time array.

                break 

    # Use today as current date, unless selected otherwise
    try:
        today = datetime.strptime(config.get('mydate'), '%Y%m%d')
    except ValueError:
        today = date.today()

    # Remove NetCDF files older than 2 days
    clean(config.get('hindpath') + '/', 2)

    localpath = config.get('hindpath') + '/' + today.strftime('%Y%m%d') + '/'
    if not os.path.isdir(localpath):
        os.makedirs(localpath)
    config['localpath'] = localpath

    # Create boundary forcing file
    logger.info(f'{now()} Creating boundary file...')
    config['bryname'] = create_bry(config)

    variables = ('zeta', 'u', 'v', 'ubar', 'vbar', 'temp', 'salt',
            'DIC', 'TALK', 'NO3', 'PO4', 'Si', 'O2', 'FER', 'NH4')
    for v in variables:
        if v in PISCES and config.get('PISCES') != 'T':
            continue # Ignore PISCES 
        selection = config.get(v) # Get user's choices for this variable
        if selection[0] == 'Y': # 'Yes', generate boundary forcing for this variable
            logger.info(f'{now()} Processing variable {v}')
            interpolate_bry_variable(config, v)

    # Write name of boundary file to copy to HPC
    with open('/log/boundary.config', 'w') as f:
        f.write(f'bryname={os.path.abspath(config.get("bryname"))}')
                
def clean(path, D):
    ''' Removes files in path older than D days '''
    old = time.time() - D * 86400
    for f in glob.glob(path + '**/croco_bry.nc', recursive=True):
        file = os.path.abspath(f)
        if os.path.getctime(file) < old:
            logger.info(f'{now()} Deleting {file}') 
            os.remove(file)

if __name__ == '__main__':
    ''' PART 1: Download NetCDF from Copernicus Marine Service '''
    try:
        copernicus()
    except Exception as e:
        logger.error("Exception in Copernicus Boundary Download: " + e.args[0])
        logger.error(traceback.format_exc())

    ''' PART 2: Create boundary forcing file '''
    try: 
        make_boundary()
    except Exception as e:
        logger.error("Exception while creating boundary forcing: " + e.args[0])
        logger.error(traceback.format_exc())

    logger.info(f'{now()} END')
