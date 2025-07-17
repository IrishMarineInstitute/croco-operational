from netCDF4 import Dataset

def create_bulk(faire, fflux, fwind, L, M, T, offset, longitude, latitude, time):
    ''' Create bulk forcing files '''

    offsetstr = offset.strftime('%Y-%m-%d')

    with Dataset(faire, 'w', format='NETCDF3_CLASSIC') as nc:
        # Dimensions
        nc.createDimension('lon', L)
        nc.createDimension('lat', M)
        nc.createDimension('time', T)

        # Longitude
        lon = nc.createVariable('lon', 'f8', dimensions=('lon'))
        lon.long_name = 'longitude'
        lon.units = 'degrees_east'
        lon.axis = 'X'
        lon[:] = longitude

        # Latitude
        lat = nc.createVariable('lat', 'f8', dimensions=('lat'))
        lat.long_name = 'latitude'
        lat.units = 'degrees_north'
        lat.axis = 'Y'
        lat[:] = latitude

        # Air pressure time
        ptime = nc.createVariable('pair_time', 'f8', dimensions=('time'))
        ptime.long_name = 'surface air pressure time'
        ptime.units = 'day'
        ptime[:] = time

        # Air temperature time
        ttime = nc.createVariable('tair_time', 'f8', dimensions=('time'))
        ttime.long_name = 'surface air temperature time'
        ttime.units = 'day'
        ttime[:] = time

        # Air humidity time
        qtime = nc.createVariable('qair_time', 'f8', dimensions=('time'))
        qtime.long_name = 'surface relative humidity time'
        qtime.units = 'day'
        qtime[:] = time

        # Cloudiness time
        ctime = nc.createVariable('cloud_time', 'f8', dimensions=('time'))
        ctime.long_name = 'cloud fraction time'
        ctime.units = 'day'
        ctime[:] = time

        # Rain time
        rtime = nc.createVariable('rain_time', 'f8', dimensions=('time'))
        rtime.long_name = 'rain fall rate time'
        rtime.units = 'day'
        rtime[:] = time

        # Evaporation time (not used)
        # etime = nc.createVariable('evap_time', 'f8', dimensions=('time'))
        # etime.long_name = 'evaporation rate time'
        # etime.units = 'day'
        # etime[:] = time

        # Air pressure
        pair = nc.createVariable('Pair', 'f8', dimensions=('time', 'lat', 'lon'))
        pair.long_name = 'surface air pressure'
        pair.units = 'millibar'
        pair.time = 'pair_time'
        pair.field = 'Pair, scalar, series'
        pair.coordinates = 'lon lat'

        # Air temperature
        tair = nc.createVariable('Tair', 'f8', dimensions=('time', 'lat', 'lon'))
        tair.long_name = 'surface air temperature'
        tair.units = 'Celsius'
        tair.time = 'tair_time'
        tair.field = 'Tair, scalar, series'
        tair.coordinates = 'lon lat'

        # Relative humidity
        qair = nc.createVariable('Qair', 'f8', dimensions=('time', 'lat', 'lon'))
        qair.long_name = 'surface air relative humidity'
        qair.units = 'percentage'
        qair.time = 'qair_time'
        qair.field = 'Qair, scalar, series'
        qair.coordinates = 'lon lat'

        # Cloud cover
        cloud = nc.createVariable('cloud', 'f8', dimensions=('time', 'lat','lon'))
        cloud.long_name = 'cloud fraction'
        cloud.units = 'nondimensional'
        cloud.time = 'cloud_time'
        cloud.field = 'cloud, scalar, series'
        cloud.coordinates = 'lon lat'

        # Rainfall rate
        rain = nc.createVariable('rain', 'f8', dimensions=('time', 'lat', 'lon'))
        rain.long_name = 'rain fall rate'
        rain.units = 'kilogram meter-2 second-1'
        rain.time = 'rain_time'
        rain.field = 'rain, scalar, series'
        rain.coordinates = 'lon lat'

        # Evaporation rate (not used)
        # e = nc.createVariable('evaporation', 'f8', dimensions=('time', 'lat', 'lon'))
        # e.long_name = 'evaporation rate'
        # e.units = 'kilogram meter-2 second-1'
        # e.time = 'evap_time'
        # e.field = 'evaporation, scalar, series'
        # e.coordinates = 'lon lat'
        

    with Dataset(fflux, 'w', format='NETCDF3_CLASSIC') as nc:
        # Dimensions
        nc.createDimension('lon', L)
        nc.createDimension('lat', M)
        nc.createDimension('time', T)

        # Longitude
        lon = nc.createVariable('lon', 'f8', dimensions=('lon'))
        lon.long_name = 'longitude'
        lon.units = 'degrees_east'
        lon.axis = 'X'
        lon[:] = longitude

        # Latitude
        lat = nc.createVariable('lat', 'f8', dimensions=('lat'))
        lat.long_name = 'latitude'
        lat.units = 'degrees_north'
        lat.axis = 'Y'
        lat[:] = latitude

        # Shortwave radiation time
        stime = nc.createVariable('srf_time', 'f8', dimensions=('time'))
        stime.long_name = 'solar shortwave radiation time'
        stime.units = 'day'
        stime[:] = time

        # Longwave radiation time
        ltime = nc.createVariable('lrf_time', 'f8', dimensions=('time'))
        ltime.long_name = 'net longwave radiation time'
        ltime.units = 'day'
        ltime[:] = time

        # Shortwave radiation
        solar = nc.createVariable('swrad', 'f8', dimensions=('time', 'lat', 'lon'))
        solar.long_name = 'solar shortwave radiation'
        solar.units = 'Watts meter-2'
        solar.time = 'srf_time'
        solar.field = 'shortwave radiation, scalar, series'
        solar.coordinates = 'lon lat'

        # Longwave radiation
        long = nc.createVariable('lwrad', 'f8', dimensions=('time', 'lat', 'lon'))
        long.long_name = 'net longwave radiation flux'
        long.units = 'Watts meter-2'
        long.time = 'lrf_time'
        long.field = 'longwave radiation, scalar, series'
        long.coordinates = 'lon lat'

        # Longwave, downwelling radiation
        down = nc.createVariable('lwrad_down', 'f8', dimensions=('time', 'lat', 'lon'))
        down.long_name = 'downwelling longwave radiation flux'
        down.units = 'Watts meter-2'
        down.time = 'lrf_time'
        down.field = 'downwelling longwave radiation, scalar, series'
        down.coordinates = 'lon lat'


    with Dataset(fwind, 'w', format='NETCDF3_CLASSIC') as nc:
        # Dimensions
        nc.createDimension('lon', L)
        nc.createDimension('lat', M)
        nc.createDimension('time', T)

        # Longitude
        lon = nc.createVariable('lon', 'f8', dimensions=('lon'))
        lon.long_name = 'longitude'
        lon.units = 'degrees_east'
        lon.axis = 'X'
        lon[:] = longitude

        # Latitude
        lat = nc.createVariable('lat', 'f8', dimensions=('lat'))
        lat.long_name = 'latitude'
        lat.units = 'degrees_north'
        lat.axis = 'Y'
        lat[:] = latitude

        # Wind time
        wtime = nc.createVariable('wind_time', 'f8', dimensions=('time'))
        wtime.long_name = 'surface wind time'
        wtime.standard_name = 'time'
        wtime.units = 'day since ' + offsetstr
        wtime[:] = time

        # u-wind 
        u = nc.createVariable('Uwind', 'f8', dimensions=('time', 'lat', 'lon'))
        u.long_name = 'surface u-wind component'
        u.standard_name = 'x_wind'
        u.units = 'meter second-1'
        u.time = 'wind_time'
        u.field = 'u-wind, scalar, series'
        u.coordinates = 'lon lat'

        # v-wind 
        v = nc.createVariable('Vwind', 'f8', dimensions=('time', 'lat', 'lon'))
        v.long_name = 'surface v-wind component'
        v.standard_name = 'y_wind'
        v.units = 'meter second-1'
        v.time = 'wind_time'
        v.field = 'v-wind, scalar, series'
        v.coordinates = 'lon lat'
