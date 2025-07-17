from datetime import datetime
from netCDF4 import Dataset
import numpy as np
import os

def create_bgc_time_ncvar(nc, name, offset, time):
    ''' Create NetCDF biogeochemistry time variable '''

    ncvar = nc.createVariable(name, 'f8', dimensions=('qbar_time'))
    ncvar.long_name = 'runoff_time'
    ncvar.units = 'days'
    ncvar.cycle_length = 0
    ncvar.long_units = 'days since ' + offset.strftime('%Y-%m-%d')
    # Write time
    ncvar[:] = time

def create_bgc_runoff_ncvar(nc, name):
    ''' Create NetCDF biogeochemistry runoff variable '''

    ncvar = nc.createVariable(name + '_src', 'f8', dimensions=('n_qbar', 'qbar_time'))
    ncvar.long_name = 'runoff ' + name.lower() + ' conc.'
    ncvar.units = 'mmol m-3'

def create_runoff(config):
    ''' Create CROCO runoff forcing file structure '''

    offset = datetime.strptime(config.get('offset'), '%Y%m%d')

    time = config.get('time'); T = len(time)

    names, I, J, DIRECTION, SENSE = [], [], [], [], []

    for i in range(1000):
        try:
            river = config[f'RIVER-{i:03d}']
            names.append(river[0])
            I.append(int(river[1]))
            J.append(int(river[2]))
            DIRECTION.append(int(river[3]))
            SENSE.append(int(river[4]))
        except KeyError:
            break # No more ESB stations to download. Exit loop

    # Get number of rivers 
    nrivers = len(J)

    if nrivers == 0:
        return 0

    # Get length of the longest river name
    strlen = 0
    for i in names:
        if len(i) > strlen:
            strlen = len(i)

    # Create names character array
    rivernames = [i.ljust(strlen) for i in names]

    rivnames = np.empty((nrivers, strlen), dtype='<U64')
    for i, name in enumerate(rivernames):
        for j, character in enumerate(name):
            rivnames[i,j] = character

    # Create runoff position array
    position = np.array([I, J]).T

    # Create runoff position array
    direction = np.array([DIRECTION, SENSE]).T

    # Absolute path to the CROCO runoff forcing file
    abspath = config.get('localpath') + 'croco_runoff.nc'
    if os.path.isfile(abspath):
        os.remove(abspath)

    with Dataset(abspath, 'w', format='NETCDF4') as nc:

        ''' Create dimensions '''
        nc.createDimension('qbar_time', T)
        nc.createDimension('runoffname_StrLen', strlen)
        nc.createDimension('n_qbar', nrivers)
        nc.createDimension('two', 2)
        nc.createDimension('temp_src_time', T)
        nc.createDimension('salt_src_time', T)

        ''' Create variables '''
        qbar_time = nc.createVariable('qbar_time', 'f8', dimensions=('qbar_time'))
        qbar_time.long_name = 'runoff time'
        qbar_time.units = 'days'
        qbar_time.cycle_length = 0
        qbar_time.long_units = 'days since ' + offset.strftime('%Y-%m-%d')
        # Write time
        qbar_time[:] = time

        runoff_name = nc.createVariable('runoff_name', 'S1', dimensions=('n_qbar', 'runoffname_StrLen'))
        runoff_name.long_name = 'runoff name'
        runoff_name[:] = rivnames

        runoff_position = nc.createVariable('runoff_position', 'f8', dimensions=('n_qbar', 'two'))
        runoff_position.long_name = 'position of the runoff (by line) in the CROCO grid'
        runoff_position[:] = position

        runoff_direction = nc.createVariable('runoff_direction', 'f8', dimensions=('n_qbar', 'two'))
        runoff_direction.long_name = 'direction/sense of the runoff (by line) in the CROCO grid'
        runoff_direction[:] = direction

        Qbar = nc.createVariable('Qbar', 'f8', dimensions=('n_qbar', 'qbar_time'))
        Qbar.long_name = 'runoff discharge'
        Qbar.units = 'm3.s-1'

        temp_src_time = nc.createVariable('temp_src_time', 'f8', dimensions=('temp_src_time'))
        temp_src_time.cycle_length = 0
        temp_src_time.long_units = 'days since ' + offset.strftime('%Y-%m-%d')
        # Write time
        temp_src_time[:] = time

        salt_src_time = nc.createVariable('salt_src_time', 'f8', dimensions=('salt_src_time'))
        salt_src_time.cycle_length = 0
        salt_src_time.long_units = 'days since ' + offset.strftime('%Y-%m-%d')
        # Write time
        salt_src_time[:] = time

        temp_src = nc.createVariable('temp_src', 'f8', dimensions=('n_qbar', 'temp_src_time'))
        temp_src.long_name = 'runoff temperature'
        temp_src.units = 'Degrees Celsius'

        salt_src = nc.createVariable('salt_src', 'f8', dimensions=('n_qbar', 'salt_src_time'))
        salt_src.long_name = 'runoff salinity'
        salt_src.units = 'psu'
        # Write salinity
        salt_src[:] = float(config.get('riverSalt'))

        if config.get('PISCES') == 'T': # If PISCES is used
            for nutrient in ('NO3', 'PO4', 'Si', 'FER', 'DIC', 'TALK', 'O2'): # Add NetCDF variables for these parameters
                create_bgc_time_ncvar(nc, nutrient.lower() + '_src_time', offset, time) # Time
                create_bgc_runoff_ncvar(nc, nutrient) # Concentration
            # Write Dissolved Inorganic Carbon
            varnc = nc.variables['DIC_src']; varnc[:] = float(config.get('riverDIC'))
            # Write Total Alkalinity 
            varnc = nc.variables['TALK_src']; varnc[:] = float(config.get('riverTALK'))

    return abspath
