from scipy.interpolate import RegularGridInterpolator
from netCDF4 import Dataset, num2date
from scoordinate import scoord2z
from datetime import datetime
import numpy as np
import glob

PISCES = ('DIC', 'TALK', 'pH', 'NO3', 'NH4', 'PO4', 'Si', 'O2', 'FER')

def vertical_interpolations(config, H, z, data, mask, variable):
    ''' Perform vertical interpolations from CMEMS product
    to CROCO boundary, where:

    config: options set in configuration file, including
            the desired CROCO vertical coordinate set up.

    H: CROCO bathymetry along boundary (n x 1) 1-D array
       where n is the length of the CROCO boundary.

    z: CMEMS product depth list (Z x 1) 1-D array
       where Z is the number of vertical levels in CMEMS.

    data: CMEMS 3-D ocean data already horizontally 
          interpolated to CROCO boundary (n x Z) 2-D array.

    mask: CROCO land/sea mask along boundary (n x 1) 1-D array
          Used to skip computations on land.
          
    variable: variable name being processed.

    Returns an N x n 2-D array, where N is the number of 
    vertical levels in CROCO and n is the length of the boundary.
     '''

    # Get CROCO vertical coordinate 
    if int(config.get('Vtransform')) == 1:
        scoord = 'old1994'
    elif int(config.get('Vtransform')) == 2:
        scoord = 'new2008'

    theta_s = float(config.get('theta_s')) # Surface stretching parameter
    theta_b = float(config.get('theta_b')) # Bottom stretching parameter
    N = int(config.get('N')) # Number of S levels
    hc = float(config.get('hc')) # Critical depth

    out = -10*np.ones((N, len(H))) # Output initialization

    for i, (h, m) in enumerate(zip(H, mask)):
        if m == 0: 
            out[:,i] = -999.9; continue # Add dummy value on land

        data_i = fill_mask(data[:,i], variable)

        [z_rho, Cs_rho, sc_rho] = scoord2z('r', 
                np.array([0]), np.array([h]),
                theta_s, theta_b, N, hc, scoord=scoord)

        out[:,i] = np.interp(-z_rho, z, data_i) # Vertical interpolation

    return out

def interp_time2d(config, time, v):
    '''      Linearly interpolate 2-D variable 
    from its native time array to the master time array ''' 

    offset = datetime.strptime(config.get('offset'), '%Y%m%d')

    # Convert times to time stamps
    time = np.array([datetime(i.year, i.month, i.day,
        i.hour, i.minute) for i in time])
    time = np.array([(i - offset).total_seconds()/86400 for i in time])

    # Load master time array
    master = config.get('time')

    # Get variable dimenions
    T, X = v.shape

    # Output initialization
    out = -10*np.ones((len(master), X))

    for i in range(X):
        out[:,i] = np.interp(master, time, v[:,i])

    return out

def interp_time3d(config, time, v):
    '''      Linearly interpolate 3-D variable 
    from its native time array to the master time array ''' 

    offset = datetime.strptime(config.get('offset'), '%Y%m%d')

    # Convert times to time stamps
    time = np.array([datetime(i.year, i.month, i.day,
        i.hour, i.minute) for i in time])
    time = np.array([(i - offset).total_seconds()/86400 for i in time])

    # Load master time array
    master = config.get('time')

    # Get variable dimenions
    T, N, X = v.shape

    # Output initialization
    out = -10*np.ones((len(master), N, X))

    for i in range(X):
        for k in range(N):
            out[:,k,i] = np.interp(master, time, v[:,k,i])

    return out

def fill_mask(data, variable):
    ''' Fill masked boundary 1-D array with nearest neighbour.
    This is used to avoid missing values along the boundaries
    in cells located close to the coast. These missing values
    result from interpolating from the Copernicus product to
    the CROCO grid. '''

    copy = np.copy(data) # Output initialization 

    # Set valid ranges for different ocean parameters
    if variable in ('temp', 'salt'):
        valid_min, valid_max = 0, 40 # Celsius, PSU   
    elif variable in ('u', 'v', 'ubar', 'vbar', 'zeta'):
        valid_min, valid_max = -5, 5 # m/s, m   
    elif variable in ('DIC', 'TALK'):
        valid_min, valid_max = 1, 3 # mol m-3
    elif variable in ('NO3', 'PO4', 'NH4', 'Si', 'FER'):
        valid_min, valid_max = 0, 100 # mmol m-3
    elif variable in ('O2',):
        valid_min, valid_max = 0, 400 # mmol m-3
    elif variable in ('pH',):
        valid_min, valid_max = 7.5, 8.5

    # Identify missing values using the range above
    mask = np.logical_or(data < valid_min, data > valid_max)

    # Get indexes of valid, unmasked (ocean) values 
    w = np.where(mask == False)[0]

    if w.size == 0:  return copy

    for i, masked in enumerate(mask): # Loop along 1-D array
        if masked: # If value is missing
            ind = w[np.argmin(abs(w - i))] # Find nearest neighbour index
            copy[i] = data[ind] # ... and replace with a valid value
    return copy

def interpolate_bry_variable(config, variable):
    ''' Interpolate CROCO ocean variable for boundary forcing '''

    OpenBoundaries = config.get('OpenBoundaries')

    gridType = {'temp': 'rho', 'salt': 'rho', 'zeta': 'rho', 'pH': 'rho',
            'DIC': 'rho', 'NO3': 'rho', 'NH4': 'rho', 'PO4': 'rho',
            'Si': 'rho', 'FER': 'rho', 'O2': 'rho', 'TALK': 'rho',
            'u': 'u', 'ubar': 'u', 'v': 'v', 'vbar': 'v'}

    gridType = gridType.get(variable)

    ''' Set variable offset, if any '''
    offset, factor = 0.0, 1.0
    if variable == 'temp':
        offset = float(config.get('tempOffset'))
    elif variable == 'salt':
        offset = float(config.get('saltOffset'))
    elif variable == 'zeta':
        offset = float(config.get('zetaOffset'))
    elif variable == 'DIC':
        factor = float(config.get('dicFactor'))
    elif variable == 'TALK':
        factor = float(config.get('talkFactor'))
    # Similar feature could be extended for PISCES...

    ''' Read CROCO grid '''
    with Dataset(config.get('grdname'), 'r') as nc:
        # Read CROCO longitude
        lon = nc.variables['lon_' + gridType][:]
        # Read CROCO latitude
        lat = nc.variables['lat_' + gridType][:]
        #Read CROCO bathymetry
        H = nc.variables['h'][:]
        # Read CROCO land/sea mask
        mask = nc.variables['mask_' + gridType][:]

    # Get CROCO grid size
    M, L = mask.shape
        
    if gridType == 'u':
        H = .5 * (H[:,0:-1] + H[:,1::]) # Bathymetry at U points
    elif gridType == 'v':
        H = .5 * (H[0:-1,:] + H[1::,:]) # Bathymetry at V points

    ''' Read from Copernicus '''
    cmemspath = config.get('cmemspath')

    f = glob.glob(cmemspath + f'/cmems-{variable}-*.nc')[0]
    # Get Copernicus variable name
    varname = config.get(variable)[2]
    # Open Copernicus file
    with Dataset(f, 'r') as nc:
        data = nc.variables[varname][:]
        # Get variable dimensions
        dimensions = nc.variables[varname].dimensions

        # Read coordinates
        for i in dimensions:
            if 'lon' in i:
                longitude = nc.variables[i][:]
            if 'lat' in i:
                latitude = nc.variables[i][:]
            if 'depth' in i:
                depth = nc.variables[i][:]
            if 'time' in i:
                time = num2date(nc.variables[i][:],
                        nc.variables[i].units)

    ''' 2-D variable processing '''
    if 'zeta' in variable or 'bar' in variable: 
        if OpenBoundaries[0]: # South
            S = -10*np.ones((len(time), L))
        if OpenBoundaries[1]: # East
            E = -10*np.ones((len(time), M))
        if OpenBoundaries[2]: # North
            N = -10*np.ones((len(time), L))
        if OpenBoundaries[3]: # West
            W = -10*np.ones((len(time), M))

        for i in range(len(time)):
            data_i = data[i,:,:]

            GridInterpolant = RegularGridInterpolator((latitude, 
                longitude), data_i)

            # Interpolate to CROCO grid
            out = GridInterpolant((lat, lon))

            if OpenBoundaries[0]: # South
                S[i,:] = fill_mask(out[0,:], variable)
            if OpenBoundaries[1]: # East
                E[i,:]  = fill_mask(out[:,-1], variable)
            if OpenBoundaries[2]: # North
                N[i,:] = fill_mask(out[-1,:], variable)
            if OpenBoundaries[3]: # West
                W[i,:]  = fill_mask(out[:,0], variable) 

        if variable != config.get('master'):
            if OpenBoundaries[0]: # South
                S = interp_time2d(config, time, S)
            if OpenBoundaries[1]: # East
                E = interp_time2d(config, time, E)
            if OpenBoundaries[2]: # North
                N = interp_time2d(config, time, N)
            if OpenBoundaries[3]: # West
                W = interp_time2d(config, time, W)


        ''' Write to CROCO boundary forcing file '''
        with Dataset(config.get('bryname'), 'a') as nc:
            if OpenBoundaries[0]: # South
                nc.variables[variable + '_south'][:] = offset + S * factor
            if OpenBoundaries[1]: # East
                nc.variables[variable + '_east'][:] = offset + E * factor
            if OpenBoundaries[2]: # North
                nc.variables[variable + '_north'][:] = offset + N * factor
            if OpenBoundaries[3]: # West
                nc.variables[variable + '_west'][:] = offset + W * factor

        return

    ''' 3-D variable processing '''
    # Output initialization
    if OpenBoundaries[0]: # South
        S3D = -10*np.ones((len(time), int(config.get('N')), L))
    if OpenBoundaries[1]: # East
        E3D = -10*np.ones((len(time), int(config.get('N')), M))
    if OpenBoundaries[2]: # North
        N3D = -10*np.ones((len(time), int(config.get('N')), L))
    if OpenBoundaries[3]: # West
        W3D = -10*np.ones((len(time), int(config.get('N')), M))
    
    for t in range(len(time)):
        if OpenBoundaries[0]: # South
            S = -10*np.ones((len(depth), L))
        if OpenBoundaries[1]: # East
            E = -10*np.ones((len(depth), M))
        if OpenBoundaries[2]: # North
            N = -10*np.ones((len(depth), L))
        if OpenBoundaries[3]: # West
            W = -10*np.ones((len(depth), M))

        for k in range(len(depth)):
            data_i = data[t,k,:,:]

            GridInterpolant = RegularGridInterpolator((latitude, 
                longitude), data_i)

            # Interpolate to CROCO grid
            out = GridInterpolant((lat, lon))

            if OpenBoundaries[0]: # South
                S[k,:] = fill_mask(out[0,:], variable) 
            if OpenBoundaries[1]: # East
                E[k,:]  = fill_mask(out[:,-1], variable)
            if OpenBoundaries[2]: # North
                N[k,:] = fill_mask(out[-1,:], variable)
            if OpenBoundaries[3]: # West
                W[k,:]  = fill_mask(out[:,0], variable) 

        if OpenBoundaries[0]:
            S3D[t,:,:] = vertical_interpolations(config, H[0,:], 
                    depth, S, mask[0,:], variable)
        if OpenBoundaries[1]:
            E3D[t,:,:] = vertical_interpolations(config, H[:,-1], 
                    depth, E, mask[:,-1], variable)
        if OpenBoundaries[2]:
            N3D[t,:,:] = vertical_interpolations(config, H[-1,:], 
                    depth, N, mask[-1,:], variable)
        if OpenBoundaries[3]: 
            W3D[t,:,:] = vertical_interpolations(config, H[:,0], 
                    depth, W, mask[:,0], variable)

    if ( variable != config.get('master') ) and ( variable not in PISCES ):
        if OpenBoundaries[0]: # South
            S3D = interp_time3d(config, time, S3D)
        if OpenBoundaries[1]: # East
            E3D = interp_time3d(config, time, E3D)
        if OpenBoundaries[2]: # North
            N3D = interp_time3d(config, time, N3D)
        if OpenBoundaries[3]: # West
            W3D = interp_time3d(config, time, W3D)

    ''' Write to CROCO boundary forcing file '''
    with Dataset(config.get('bryname'), 'a') as nc:
        if OpenBoundaries[0]: # South
            nc.variables[variable + '_south'][:] = offset + S3D * factor
        if OpenBoundaries[1]: # East
            nc.variables[variable + '_east'][:] = offset + E3D * factor
        if OpenBoundaries[2]: # North
            nc.variables[variable + '_north'][:] = offset + N3D * factor
        if OpenBoundaries[3]: # West
            nc.variables[variable + '_west'][:] = offset + W3D * factor

    return
