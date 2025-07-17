from netCDF4 import Dataset
import PyCO2SYS as pyco2
import numpy as np
import gsw
import os

def total_alkalinity(config, idatestr, edatestr):
    ''' Total alkalinity calculation '''
    # Path to downloaded CMEMS files
    path = config.get('cmemspath') + '/'
    
    filename = f'{path}cmems-DIC-{idatestr}-{edatestr}.nc' 
    if os.path.isfile(filename):
        with Dataset(filename) as nc:
            # Read longitude
            lon = nc.variables['longitude'][:]; L = len(lon)
            # Read latitude
            lat = nc.variables['latitude'][:];  M = len(lat)
            # Read depth
            depth = nc.variables['depth'][:];   N = len(depth)
            # Read time 
            time = nc.variables['time'][:];     T = len(time)
            # Read time units
            units = nc.variables['time'].units
            # Read Dissolved Inorganic Carbon
            DIC = nc.variables[config.get('DIC')[2]][:]
    else:
        raise FileNotFoundError('Error while calculating Total Alkalinity: DIC file is missing')
        
    # Reshape longitude to fit 4-D array
    LON = np.tile(lon, (T, M, N, 1))
    LON = np.transpose(LON, (0, 2, 1, 3))
    # Reshape latitude to fit 4-D array
    LAT = np.tile(lat, (T, L, N, 1))
    LAT = np.transpose(LAT, (0, 2, 3, 1))
    # Reshape depth to fit 4-D array
    DEPTH = np.tile(depth, (T, M, L, 1))
    DEPTH = np.transpose(DEPTH, (0, 3, 1, 2))

    filename = f'{path}cmems-temp-{idatestr}-{edatestr}.nc' 
    if os.path.isfile(filename):
        with Dataset(filename) as nc:            
            # Read temperature
            thetao = nc.variables[config.get('temp')[2]][:]
    else:
        raise FileNotFoundError('Error while calculating Total Alkalinity: temperature file is missing')

    filename = f'{path}cmems-salt-{idatestr}-{edatestr}.nc' 
    if os.path.isfile(filename):
        with Dataset(filename) as nc:
            # Read salinity
            so = nc.variables[config.get('salt')[2]][:]
    else:
        raise FileNotFoundError('Error while calculating Total Alkalinity: salinity file is missing')

    filename = f'{path}cmems-pH-{idatestr}-{edatestr}.nc' 
    if os.path.isfile(filename):
        with Dataset(filename) as nc:
            # Read pH
            pH = nc.variables[config.get('pH')[2]][:]
    else:
        raise FileNotFoundError('Error while calculating Total Alkalinity: pH file is missing')

    filename = f'{path}cmems-NH4-{idatestr}-{edatestr}.nc' 
    if os.path.isfile(filename):
        with Dataset(filename) as nc:
            # Read ammonia
            NH4 = nc.variables[config.get('NH4')[2]][:]
    else:
        raise FileNotFoundError('Error while calculating Total Alkalinity: NH4 file is missing')

    filename = f'{path}cmems-PO4-{idatestr}-{edatestr}.nc' 
    if os.path.isfile(filename):
        with Dataset(filename) as nc:
            # Read phosphate
            PO4 = nc.variables[config.get('PO4')[2]][:]
    else:
        raise FileNotFoundError('Error while calculating Total Alkalinity: PO4 file is missing')

    filename = f'{path}cmems-Si-{idatestr}-{edatestr}.nc' 
    if os.path.isfile(filename):
        with Dataset(filename) as nc:
            # Read silicon
            Si = nc.variables[config.get('Si')[2]][:]
    else:
        raise FileNotFoundError('Error while calculating Total Alkalinity: Si file is missing')

    # Calculate Absolute Salinity
    SA = gsw.conversions.SA_from_SP(so, DEPTH, LON, LAT)
    # Calculate Conservative Temperature
    CT = gsw.conversions.CT_from_pt(SA, thetao)
    # Calculate density
    density = gsw.density.rho(SA, CT, DEPTH)

    # Transform DIC units
    DIC = 1e6 * np.divide(DIC, density) # From mol m-3 to umol kg-1

    # Convert nutrient units
    NH4 = 1e3 * np.divide(NH4, density) # From mmol m-3 to umol kg-1
    PO4 = 1e3 * np.divide(PO4, density) # From mmol m-3 to umol kg-1
    Si  = 1e3 * np.divide(Si,  density) # From mmol m-3 to umol kg-1

    # Calculate carbonate system
    co2sys = pyco2.sys(par1=DIC, par2=pH, par1_type=2, par2_type=3,
            salinity=so, temperature=thetao, pressure=DEPTH,
            total_silicate=Si, total_phosphate=PO4, total_ammonia=NH4)

    # Get Total Alkalinity
    TALK = 1e-6 * np.multiply(co2sys.get('alkalinity'), density)

    # Save to NetCDF. Total alkalinity will be read from this NetCDF for interpolations
    filename = f'{path}cmems-TALK-{idatestr}-{edatestr}.nc' 
    with Dataset(filename, 'w', format='NETCDF4') as nc:
        # NetCDF should have the same structure as a regular CMEMS file
        nc.createDimension('longitude', L)
        nc.createDimension('latitude',  M)
        nc.createDimension('depth', N)
        nc.createDimension('time',  T)

        # Longitude
        lonvar = nc.createVariable('longitude', 'f8', dimensions=('longitude'))
        lonvar.standard_name = 'longitude'
        lonvar.units = 'degree_east'
        lonvar[:] = lon

        # Latitude
        latvar = nc.createVariable('latitude', 'f8', dimensions=('latitude'))
        latvar.standard_name = 'latitude'
        latvar.units = 'degree_north'
        latvar[:] = lat

        # Time
        timevar = nc.createVariable('time', 'f8', dimensions=('time'))
        timevar.standard_name = 'time'
        timevar.units = units
        timevar[:] = time

        # Depth
        depthvar = nc.createVariable('depth', 'f8', dimensions=('depth'))
        depthvar.standard_name = 'depth'
        depthvar.units = 'meter'
        depthvar[:] = depth

        # Total alkalinity
        talk = nc.createVariable('talk', 'f8', dimensions=('time',
            'depth', 'latitude', 'longitude'), fill_value=-32767)
        talk.long_name = 'total alkalinity'
        talk.units = 'mmol m-3'
        talk[:] = TALK
