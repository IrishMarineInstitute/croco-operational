from datetime import datetime
from netCDF4 import Dataset
import numpy as np
import argparse
import glob
import os

def scoord(N):
    l = np.linspace(-1, 0, N+1)
    return .5*(l[0:-1] + l[1:])

def OpenDriftCompliant(file, offset, destpath):
    ''' 
        Takes a CROCO history file and creates a copy that is OpenDrift compliant.
        
        On INPUT:
            
            FILE: CROCO history file
            
            OFFSET: CROCO reference time with format like in 19680523         

            DESTPATH: destination path for new files
            
        On OUTPUT:
            
            A new NetCDF that is OpenDrift compliant.
        
    '''
    
    grid = 'croco_grd.nc'
    
    # Get time units
    units = 'seconds since ' + datetime.strptime(offset, '%Y%m%d').strftime('%Y-%m-%d')
            
    fname = destpath + (os.path.basename(file)).replace('.nc', '_OPENDRIFT.nc'); print(f'Creating {fname}...')    
    with Dataset(fname, 'w', format='NETCDF4') as nc, Dataset(grid, 'r') as ng, Dataset(file, 'r') as nf:
        # Get dimensions of RHO grid
        Mp, Lp = ng.variables['h'].shape
        # Get xi_u and eta_v dimensions 
        Lu, Mv = Lp - 1, Mp -1 
                    
        # Read vertical transformation equation
        Vtransform = ng.variables['Vtransform'][:]
        # Read critical depth
        hc = ng.variables['hc'][:]
        # Read stretching curves at RHO points
        try:
            Cs_r = ng.variables['Cs_r'][:]
        except KeyError:
            Cs_r = ng.variables['Cs_rho'][:]
        
        # Get number of vertical levels
        N = nf.dimensions['s_rho'].size
        # Get number of time records
        T = nf.dimensions['time'].size
        
        ''' Create global attributes ''' 
        nc.title = os.path.basename(fname)
        nc.producer = 'Marine Institute'
        nc.history = 'Created on ' + datetime.now().strftime('%d-%b-%Y %H:%M:%S')
        nc.type = 'CROCO history file modified to be OpenDrift compliant'
        
        ''' Create dimensions '''
        nc.createDimension('xi_rho',  Lp)
        nc.createDimension('xi_u',    Lu)
        nc.createDimension('xi_v',    Lp)
        nc.createDimension('xi_psi',  Lu)
        nc.createDimension('eta_rho', Mp)
        nc.createDimension('eta_u',   Mp)
        nc.createDimension('eta_v',   Mv)
        nc.createDimension('eta_psi', Mv)
        nc.createDimension('s_rho',    N)
        nc.createDimension('s_w',      N+1)
        nc.createDimension('time',     T)
        
        ''' Create variables needed by OpenDrift '''
        # Vertical coordinate transformation equation
        Vtransformvar = nc.createVariable('Vtransform', 'u4', dimensions=())
        Vtransformvar.long_name = 'vertical terrain-following transformation equation'
        Vtransformvar[:] = Vtransform
        
        # Critical depth
        hcvar = nc.createVariable('hc', 'f8', dimensions=())
        hcvar.long_name = 'S-coordinate parameter, critical depth'
        hcvar.units = 'meter'
        hcvar[:] = hc
        
        # S-coordinate
        svar = nc.createVariable('s_rho', 'f4', dimensions=('s_rho',))
        svar.long_name = 'S-coordinate at RHO-points'
        svar.axis = 'Z'
        svar.positive = 'up'
        svar.standard_name = 'ocean_s_coordinate_g2'
        svar.Vtransform = Vtransform
        svar.formula_terms = 's: s_rho C: Cs_rho eta: zeta depth: h depth_c: hc'
        svar[:] = scoord(N)
        
        # S-stretching curves
        csvar = nc.createVariable('Cs_r', 'f8', dimensions=('s_rho',))
        csvar.long_name = 'S-coordinate stretching curves at RHO-points'
        csvar.units = 'nondimensional'
        csvar.valid_min = -1
        csvar.valid_max = 0
        csvar[:] = Cs_r
        
        # Grid rotation angle
        anglevar = nc.createVariable('angle', 'f8', dimensions=('eta_rho', 'xi_rho'))
        anglevar.long_name = 'angle between XI-axis and EAST'
        anglevar.units = 'radians'
        anglevar[:] = ng.variables['angle'][:]
        
        # Bathymetry
        hvar = nc.createVariable('h', 'f8', dimensions=('eta_rho', 'xi_rho'))
        hvar.long_name = 'bathymetry at RHO-points'
        hvar.units = 'meter'
        print('   Writing bathymetry'); hvar[:] = ng.variables['h'][:]
                
        for g in ('rho', 'u', 'v', 'psi'):
            # Add longitude variable
            print('lon_' + g)
            lonvar = nc.createVariable('lon_' + g, 'f8', dimensions=('eta_' + g, 'xi_' + g))
            lonvar.long_name = 'longitude of ' + g.upper() + '-points'
            lonvar.units = 'degree_east'
            lonvar.standard_name = 'longitude'
            lonvar.field = 'lon_' + g + ', scalar'
            print(f'   Writing lon_{g}'); lonvar[:] = ng.variables['lon_' + g][:]
                        
            # Add latitude variable
            print('lat_' + g)
            latvar = nc.createVariable('lat_' + g, 'f8', dimensions=('eta_' + g, 'xi_' + g))
            latvar.long_name = 'latitude of ' + g.upper() + '-points'
            latvar.units = 'degree_north'
            latvar.standard_name = 'latitude'
            latvar.field = 'lat_' + g + ', scalar'
            print(f'   Writing lat_{g}'); latvar[:] = ng.variables['lat_' + g][:]
            
            # Add mask variable
            print('mask_' + g)
            maskvar = nc.createVariable('mask_' + g, 'f8', dimensions=('eta_' + g, 'xi_' + g))
            maskvar.long_name = 'mask on ' + g.upper() + '-points'
            maskvar.flag_values = [0, 1]
            maskvar.flag_meanings = 'land water'
            maskvar.grid = 'grid'            
            maskvar.coordinates = 'lon_' + g + ' lat_' + g
            print(f'   Writing mask_{g}'); maskvar[:] = ng.variables['mask_' + g][:]
            
        # Time
        timevar = nc.createVariable('time', 'f8', dimensions=('time',))
        timevar.standard_name = 'time'
        timevar.units = units
        print('   Writing time'); timevar[:] = nf.variables['time'][:]
        
        # Sea level
        zetavar = nc.createVariable('zeta', 'f4', dimensions=('time', 'eta_rho', 'xi_rho'))
        zetavar.standard_name = 'sea_surface_height'
        zetavar.units = 'meter'
        print('   Writing sea level'); zetavar[:] = nf.variables['zeta'][:]
        
        # u-velocity
        uvar = nc.createVariable('u', 'f4', dimensions=('time', 's_rho', 'eta_u', 'xi_u'))
        uvar.standard_name = 'sea_water_x_velocity'
        uvar.units = 'meter second-1'
        print('   Writing u-velocity'); uvar[:] = nf.variables['u'][:]
        
        # v-velocity
        vvar = nc.createVariable('v', 'f4', dimensions=('time', 's_rho', 'eta_v', 'xi_v'))
        vvar.standard_name = 'sea_water_y_velocity'
        vvar.units = 'meter second-1'
        print('   Writing v-velocity'); vvar[:] = nf.variables['v'][:]
        
        # w-velocity
        wvar = nc.createVariable('w', 'f4', dimensions=('time', 's_rho', 'eta_rho', 'xi_rho'))
        wvar.standard_name = 'upward_sea_water_velocity'
        wvar.units = 'meter second-1'
        print('   Writing upward velocity'); wvar[:] = nf.variables['w'][:]
        
        # Seawater temperature (for OpenOil)
        tempvar = nc.createVariable('temp', 'f4', dimensions=('time', 's_rho', 'eta_rho', 'xi_rho'))
        tempvar.standard_name = 'sea_water_temperature'
        tempvar.units = 'Celsius'
        print('   Writing seawater temperature'); tempvar[:] = nf.variables['temp'][:]
        
        # Seawater salinity (for OpenOil)
        saltvar = nc.createVariable('salt', 'f4', dimensions=('time', 's_rho', 'eta_rho', 'xi_rho'))
        saltvar.standard_name = 'sea_water_salinity'
        print('   Writing seawater salinity'); saltvar[:] = nf.variables['salt'][:]
        
        # Turbulent generic length scale
        glsvar = nc.createVariable('gls', 'f4', dimensions=('time', 's_w', 'eta_rho', 'xi_rho'))
        glsvar.standard_name = 'turbulent_generic_length_scale'
        glsvar.units = 'meter3 second-2'
        print('   Writing turbulent generic length scale'); glsvar[:] = nf.variables['gls'][:]
        
        # Turbulent kinetic energy
        tkevar = nc.createVariable('tke', 'f4', dimensions=('time', 's_w', 'eta_rho', 'xi_rho'))
        tkevar.standard_name = 'turbulent_kinetic_energy'
        tkevar.units = 'meter2 second-2'
        print('   Writing turbulent kinetic energy'); tkevar[:] = nf.variables['tke'][:]
        
        # Ocean vertical diffusivity
        aksvar = nc.createVariable('AKs', 'f4', dimensions=('time', 's_w', 'eta_rho', 'xi_rho'))
        aksvar.standard_name = 'ocean_vertical_diffusivity'
        aksvar.units = 'meter2 second-1'
        print('   Writing ocean vertical diffusivity'); aksvar[:] = nf.variables['AKs'][:]

def main():

    msg = '''Given an INPUT DIRECTORY (-i), an OUTPUT DIRECTORY (-o) and baseline REFERENCE (-r) for CROCO time (e.g. "19680523"), this 
             function copies CROCO history files from input directory to output directory but with some modifications that makes
             CROCO files compliant with OpenDrift. '''

    # Initialize argument parser
    parser = argparse.ArgumentParser(description=msg)
    # Define command-line arguments
    parser.add_argument('-i', '--Inputdir', help='Input directory to search for CROCO files')
    parser.add_argument('-o', '--Outputdir', help='Output directoy to save the transformed, OpenDrift-compliant CROCO files')
    parser.add_argument('-r', '--Reference', help='Reference baseline for time used in CROCO')

    # Read arguments from command line
    args = parser.parse_args()
    if args.Inputdir:
        ipath = args.Inputdir
    else:
        return

    if args.Outputdir:
        opath = args.Outputdir
    else:
        return

    if args.Reference:
        offset = args.Reference
    else:
        return

    ''' Remove all contents in output directory first '''
    files = sorted(glob.glob(opath + '*.nc'))
    for f in files:
        os.remove(f)

    ''' Make files OpenDrift compliant '''
    files = sorted(glob.glob(ipath + '*.nc'))
    for f in files:
        print(os.path.basename(f))
        OpenDriftCompliant(f, offset, opath)

if __name__ == '__main__':
    main()
