from datetime import datetime
from netCDF4 import Dataset
import numpy as np
import os

from metpy.calc import dewpoint_from_relative_humidity
from metpy.calc import specific_humidity_from_dewpoint
from metpy.units import units

long_name = dict(
        MSL = 'mean_sea_level_pressure',
        T2M = '2m_temperature',
        TP = 'total_precipitation',
        Q = 'specific_humidity',
        SSR = 'surface_net_solar_radiation',
        STRD = 'surface_thermal_radiation_downwards',
        U10M = '10m_u_component_of_wind',
        V10M = '10m_v_component_of_wind',
        )

def relative2specific(MSL, T2M, Q):
    ''' Convert relative humidity to specific humidity '''
    
    temperature = units.Quantity(T2M, "degK")
    humidity = units.Quantity(Q, "percent")
    pressure = units.Quantity(MSL, "pascal")
    dewpoint = dewpoint_from_relative_humidity(temperature, humidity)
    return specific_humidity_from_dewpoint(pressure, dewpoint)

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

def ecmwf2croco(faire, fflux, fwind, year, month):
    ''' Generate CROCO online bulk forcing files '''

    config = configuration()

    # Get model boundaries
    W, E = float(config.get('west'))-.1,  float(config.get('east'))+.1
    S, N = float(config.get('south'))-.1, float(config.get('north'))+.1

    path, offset = os.path.dirname(faire), config.get('offset')

    offset = datetime.strptime(offset, '%Y%m%d').strftime('days since %Y-%m-%d')

    # Process AIR
    with Dataset(faire, 'r') as nc:
        # Read longitude 
        lon = nc.variables['lon'][:]
        i0, i1 = np.argmin(abs(lon - W)), np.argmin(abs(lon - E)) + 1
        lon = lon[i0:i1]

        # Read latitude
        lat = nc.variables['lat'][:]
        j0, j1 = np.argmin(abs(lat - S)), np.argmin(abs(lat - N)) + 1
        lat = lat[j0:j1]
   
        # Read time
        time = nc.variables['pair_time'][:]

        # Read air pressure. Convert to Pascals
        MSL = 100 * nc.variables['Pair'][:, j0:j1, i0:i1]
        create_cdf(path, lon, lat, time, MSL, 'MSL', year, month, offset)

        # Read air temperature. Convert to Kelvin
        T2M = 273.15 + nc.variables['Tair'][:, j0:j1, i0:i1]
        create_cdf(path, lon, lat, time, T2M, 'T2M', year, month, offset)

        # Read relative humidity. Convert to specific humidity
        Q = relative2specific(MSL, T2M, nc.variables['Qair'][:, j0:j1, i0:i1])
        create_cdf(path, lon, lat, time, Q, 'Q', year, month, offset)

        # Read total precipitation
        TP = nc.variables['rain'][:, j0:j1, i0:i1]
        create_cdf(path, lon, lat, time, TP, 'TP', year, month, offset)

    # Process AIR
    with Dataset(fflux, 'r') as nc:
        var1, var2 = ('swrad', 'lwrad_down'), ('SSR', 'STRD')
        for v1, v2 in zip(var1, var2):
            create_cdf(path, lon, lat, time, nc.variables[v1][:, j0:j1, i0:i1],
                    v2, year, month, offset)

    # Process WIND 
    with Dataset(fwind, 'r') as nc:
        var1, var2 = ('Uwind', 'Vwind'), ('U10M', 'V10M')
        for v1, v2 in zip(var1, var2):
            create_cdf(path, lon, lat, time, nc.variables[v1][:, j0:j1, i0:i1],
                    v2, year, month, offset)

def create_cdf(path, lon, lat, time, data, name, year, month, offset):
    ''' Create online bulk forcing monthly file '''

    units = dict(
            MSL = 'Pa', T2M = 'K', TP = 'kg m-2 s-1', Q = 'kg kg-1',
            SSR = 'W m-2', STRD = 'W m-2', U10M = 'm s-1', V10M = 'm s-1')


    filename = path + '/' + name + '_Y' + str(year) + 'M%02d' % month + '.nc'

    with Dataset(filename, 'w', format='NETCDF4') as nc:
        nc.createDimension('lon', len(lon))
        nc.createDimension('lat', len(lat))
        nc.createDimension('time', len(time))

        lonvar = nc.createVariable('lon', 'f4', dimensions=('lon'))
        lonvar.long_name = 'longitude of RHO-points'
        lonvar.units = 'degree_east'
        lonvar[:] = lon

        latvar = nc.createVariable('lat', 'f4', dimensions=('lat'))
        latvar.long_name = 'latitude of RHO-points'
        latvar.units = 'degree_north'
        latvar[:] = lat

        timevar = nc.createVariable('time', 'f8', dimensions=('time'))
        timevar.long_name = 'Time'
        timevar.units = offset
        timevar[:] = time

        datavar = nc.createVariable(name, 'f4', dimensions=('time', 'lat', 'lon'))
        datavar.long_name = long_name.get(name)
        datavar.units = units.get(name)
        datavar.missing_value = 9999
        datavar[:] = data

    with open('/log/bulk-weekly-abspath.config', 'a') as f:
        f.write(f'{os.path.abspath(filename)}\n')
    with open('/log/bulk-weekly-basename.config', 'a') as f:
        f.write(f'{os.path.basename(filename)}\n')

