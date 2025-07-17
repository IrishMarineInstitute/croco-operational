from datetime import datetime
from netCDF4 import Dataset
import xarray as xr
import numpy as np

def to_datetime(date):
    ''' Converts a numpy datetime64 to a Python datetime '''

    timestamp = ((date - np.datetime64('1970-01-01T00:00:00'))
                 / np.timedelta64(1, 's'))
    return datetime.utcfromtimestamp(timestamp)

def rh(t2m, d2m):
    ''' Calculate relative humidity '''

    T0 = 273.16
    E = 0.611 * np.exp(5423 * ((1/T0)-(1./d2m)))
    Es = 0.611 * np.exp(5423 * ((1/T0)-(1./t2m)))
    return 100 * (E/Es)

def write_bulk(faire, fflux, fwind, time, index, grib1, grib2=''):
    ''' Read ECMWF Grib file '''

    eflag = False # Error flag

    with xr.load_dataset(grib1, engine='cfgrib') as ds:
        # Read time
        t = to_datetime(ds.variables.get('valid_time').data)
        # Check time is correct
        try:
            assert(time == t)
        except AssertionError:
            eflag = True; return eflag
        
        # Air pressure. Convert to millibar
        msl = .01*np.flip(ds.variables.get('msl').data, axis=0)
        if np.any(np.isnan(msl)):
            eflag = True; return eflag
        with Dataset(faire, 'a') as nc:
            nc.variables['Pair'][index, :, :] = msl

        # Air temperature
        t2m = np.flip(ds.variables.get('t2m').data, axis=0)
        if np.any(np.isnan(t2m)):
            eflag = True; return eflag
        with Dataset(faire, 'a') as nc:
            nc.variables['Tair'][index, :, :] = t2m - 273.15 # Celsius

        # Relative humidity. Calculate from dewpoint temperature
        d2m = rh(t2m, np.flip(ds.variables.get('d2m').data, axis=0))
        if np.any(np.isnan(d2m)):
            eflag = True; return eflag
        with Dataset(faire, 'a') as nc:
            nc.variables['Qair'][index, :, :] = d2m

        # Total cloud cover
        tcc = np.flip(ds.variables.get('tcc').data, axis=0)
        if np.any(np.isnan(tcc)):
            eflag = True; return eflag
        with Dataset(faire, 'a') as nc:
            nc.variables['cloud'][index, :, :] = tcc

        # Rainfall rate
        tp = np.flip(ds.variables.get('tp').data, axis=0)
        if grib2:
            with xr.load_dataset(grib2, engine='cfgrib') as ds2:
                tp2 = np.flip(ds2.variables.get('tp').data, axis=0)
            # Subtract  
            tp -= tp2
        # This is accumulated rainfal [m] over 1 hour. Convert to kg m-2 s-1
        tp = 1000 * tp / 3600 
        # Get rid of negative values resulting from subtraction
        tp[tp < 0] = 0
        if np.any(np.isnan(tp)):
            eflag = True; return eflag
        with Dataset(faire, 'a') as nc:
            nc.variables['rain'][index, :, :] = tp

        # Solar shortwave radiation
        ssr = np.flip(ds.variables.get('ssr').data, axis=0)
        if grib2:
            with xr.load_dataset(grib2, engine='cfgrib') as ds2:
                ssr2 = np.flip(ds2.variables.get('ssr').data, axis=0)
            # Subtract
            ssr -= ssr2
        # Convert to Watts m-2
        ssr = ssr / 3600
        if np.any(np.isnan(ssr)):
            eflag = True; return eflag
        with Dataset(fflux, 'a') as nc:
            nc.variables['swrad'][index, :, :] = ssr

        # Net longwave radiation
        str = np.flip(ds.variables.get('str').data, axis=0)
        if grib2:
            with xr.load_dataset(grib2, engine='cfgrib') as ds2:
                str2 = np.flip(ds2.variables.get('str').data, axis=0)
            # Subtract
            str -= str2
        # Convert to Watts m-2
        str = str / 3600
        if np.any(np.isnan(str)):
            eflag = True; return eflag
        with Dataset(fflux, 'a') as nc:
            nc.variables['lwrad'][index, :, :] = str

        # Downwelling longwave radiation
        strd = np.flip(ds.variables.get('strd').data, axis=0)
        if grib2:
            with xr.load_dataset(grib2, engine='cfgrib') as ds2:
                strd2 = np.flip(ds2.variables.get('strd').data, axis=0)
            # Subtract
            strd -= strd2
        # Convert to Watts m-2
        strd = strd / 3600
        if np.any(np.isnan(strd)):
            eflag = True; return eflag
        with Dataset(fflux, 'a') as nc:
            nc.variables['lwrad_down'][index, :, :] = strd

        # wind
        u10 = np.flip(ds.variables.get('u10').data, axis=0)
        if np.any(np.isnan(u10)):
            eflag = True; return eflag
        with Dataset(fwind, 'a') as nc:
            nc.variables['Uwind'][index, :, :] = u10
        v10 = np.flip(ds.variables.get('v10').data, axis=0)
        if np.any(np.isnan(v10)):
            eflag = True; return eflag
        with Dataset(fwind, 'a') as nc:
            nc.variables['Vwind'][index, :, :] = v10

        return eflag
