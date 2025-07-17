from netCDF4 import Dataset
from datetime import date
from scoordinate import scoord2z
import numpy as np
import os

def create_bry(config):
    ''' Create the structure of a CROCO boundary file
    following the options in the 'config' dictionary '''

    time = config.get('time'); T = len(time)
    if config.get('PISCES') == 'T':
        pisces_time = config.get('pisces-time'); TPIS = len(pisces_time)

    OpenBoundaries = config.get('OpenBoundaries')

    if int(config.get('Vtransform')) == 1:
        scoord = 'old1994'
    elif int(config.get('Vtransform')) == 2:
        scoord = 'new2008'

    ''' Read grid '''
    with Dataset(config.get('grdname'), 'r') as nc:
        # Get grid dimensions
        Mp, Lp = nc.variables['mask_rho'].shape

    L, M = Lp-1, Mp-1

    # Absolute path to the CROCO boundary forcing file
    abspath = config.get('localpath') + config.get('bryname')
    if os.path.isfile(abspath):
        os.remove(abspath)

    with Dataset(abspath, 'w', format='NETCDF4'):
        ''' Create global attributes '''
        nc.title = config.get('title')
        nc.date = date.today().strftime('%Y-%b-%d')
        nc.clim_file = config.get('bryname')
        nc.grd_file = config.get('grdname')
        nc.type = 'BOUNDARY file'
        nc.history = 'CROCO'

        ''' Create dimensions '''
        nc.createDimension('one', 1)
        nc.createDimension('s_rho', int(config.get('N')))
        nc.createDimension('s_w', int(config.get('N'))+1)
        nc.createDimension('xi_rho', Lp)
        nc.createDimension('eta_rho', Mp)
        nc.createDimension('xi_u', L)
        nc.createDimension('eta_v', M)
        nc.createDimension('bry_time', T)
        if config.get('temp')[0] == 'Y':
            nc.createDimension('temp_time', T)
        if config.get('salt')[0] == 'Y':
            nc.createDimension('salt_time', T)
        if config.get('ubar')[0] == 'Y':
            nc.createDimension('v2d_time', T)
        if config.get('u')[0] == 'Y':
            nc.createDimension('v3d_time', T)
        if config.get('zeta')[0] == 'Y':
            nc.createDimension('ssh_time', T)
            nc.createDimension('zeta_time', T)
        if config.get('PISCES') == 'T':
            if config.get('DIC')[0] == 'Y': 
                nc.createDimension('dic_time', TPIS)
                nc.createDimension('talk_time', TPIS)
            if config.get('NO3')[0] == 'Y':
                nc.createDimension('no3_time', TPIS)
            if config.get('NH4')[0] == 'Y':
                nc.createDimension('nh4_time', TPIS)
            if config.get('PO4')[0] == 'Y':
                nc.createDimension('po4_time', TPIS)
            if config.get('Si')[0] == 'Y':
                nc.createDimension('si_time', TPIS)
            if config.get('FER')[0] == 'Y':
                nc.createDimension('fer_time', TPIS)
            if config.get('O2')[0] == 'Y':
                nc.createDimension('o2_time', TPIS)

        ''' Create variables '''
        spherical = nc.createVariable('spherical', 'S1', dimensions=('one'))
        spherical.long_name = 'grid type logical switch'
        spherical.flag_values = 'T, F'
        spherical.flag_meanings = 'spherical Cartesian'

        vtransform = nc.createVariable('Vtransform', 'u1', dimensions=('one'))
        vtransform.long_name = 'vertical terrain-following transformation equation'

        vstretching = nc.createVariable('Vstretching', 'u1', dimensions=('one'))
        vstretching.long_name = 'vertical terrain-following stretching function'

        tstart = nc.createVariable('tstart', 'f8', dimensions=('one'))
        tstart.long_name = 'start processing day'
        tstart.units = 'day'

        tend = nc.createVariable('tend', 'f8', dimensions=('one'))
        tend.long_name = 'end processing day'
        tend.units = 'day'

        theta_s = nc.createVariable('theta_s', 'f8', dimensions=('one'))
        theta_s.long_name = 'S-coordinate surface control parameter'
        theta_s.units = 'nondimensional'

        theta_b = nc.createVariable('theta_b', 'f8', dimensions=('one'))
        theta_b.long_name = 'S-coordinate bottom control parameter'
        theta_b.units = 'nondimensional'

        Tcline = nc.createVariable('Tcline', 'f8', dimensions=('one'))
        Tcline.long_name = 'S-coordinate surface/bottom layer width'
        Tcline.units = 'meter'

        hc = nc.createVariable('hc', 'f8', dimensions=('one'))
        hc.long_name = 'S-coordinate parameter, critical depth'
        hc.units = 'meter'

        sc_r = nc.createVariable('sc_r', 'f8', dimensions=('s_rho'))
        sc_r.long_name = 'S-coordinate at RHO-points'
        sc_r.valid_min = -1.0
        sc_r.valid_max =  0.0
        sc_r.positive = 'up'

        if config.get('Vtransform') == 1:
            sc_r.standard_name = 'ocean_s_coordinate_g1'
        elif config.get('Vtransform') == 2:
            sc_r.standard_name = 'ocean_s_coordinate_g2'
        sc_r.formula_terms = 's: s_rho C: Cs_r eta: zeta depth: h depth_c: hc'

        sc_w = nc.createVariable('sc_w', 'f8', dimensions=('s_w'))
        sc_w.long_name = 'S-coordinate at W-points'
        sc_w.valid_min = -1.0
        sc_w.valid_max =  0.0
        sc_w.positive = 'up'

        if config.get('Vtransform') == 1:
            sc_w.standard_name = 'ocean_s_coordinate_g1'
        elif config.get('Vtransform') == 2:
            sc_w.standard_name = 'ocean_s_coordinate_g2'
        sc_w.formula_terms = 's: s_w C: Cs_w eta: zeta depth: h depth_c: hc'

        Cs_r = nc.createVariable('Cs_r', 'f8', dimensions=('s_rho'))
        Cs_r.long_name = 'S-coordinate stretching curves at RHO-points'
        Cs_r.units = 'nondimensional'
        Cs_r.valid_min = -1
        Cs_r.valid_max =  0

        Cs_w = nc.createVariable('Cs_w', 'f8', dimensions=('s_w'))
        Cs_w.long_name = 'S-coordinate stretching curves at W-points'
        Cs_w.units = 'nondimensional'
        Cs_w.valid_min = -1
        Cs_w.valid_max =  0

        bry_time = nc.createVariable('bry_time', 'f8', dimensions=('bry_time'))
        bry_time.long_name = 'time for boundary climatology'
        bry_time.units = 'day'
        bry_time.calendar = '360.0 days in every year'
        bry_time.cycle_length = float(config.get('cycle'))

        if config.get('temp')[0] == 'Y':
            temp_time = nc.createVariable('temp_time', 'f8', dimensions=('temp_time'))
            temp_time.long_name = 'time for temperature climatology'
            temp_time.units = 'day'
            temp_time.calendar = '360.0 days in every year'
            temp_time.cycle_length = float(config.get('cycle'))

        if config.get('salt')[0] == 'Y':
            salt_time = nc.createVariable('salt_time', 'f8', dimensions=('salt_time'))
            salt_time.long_name = 'time for salinity climatology'
            salt_time.units = 'day'
            salt_time.calendar = '360.0 days in every year'
            salt_time.cycle_length = float(config.get('cycle'))

        if config.get('ubar')[0] == 'Y' or config.get('vbar')[0] == 'Y':
            v2d_time = nc.createVariable('v2d_time', 'f8', dimensions=('v2d_time'))
            v2d_time.long_name = 'time for 2D velocity climatology'
            v2d_time.units = 'day'
            v2d_time.calendar = '360.0 days in every year'
            v2d_time.cycle_length = float(config.get('cycle'))

        if config.get('u')[0] == 'Y' or config.get('v')[0] == 'Y':
            v3d_time = nc.createVariable('v3d_time', 'f8', dimensions=('v3d_time'))
            v3d_time.long_name = 'time for 3D velocity climatology'
            v3d_time.units = 'day'
            v3d_time.calendar = '360.0 days in every year'
            v3d_time.cycle_length = float(config.get('cycle'))

        if config.get('zeta')[0] == 'Y':
            ssh_time = nc.createVariable('ssh_time', 'f8', dimensions=('ssh_time'))
            ssh_time.long_name = 'time for sea surface height'
            ssh_time.units = 'day'
            ssh_time.calendar = '360.0 days in every year'
            ssh_time.cycle_length = float(config.get('cycle'))

            zeta_time = nc.createVariable('zeta_time', 'f8', dimensions=('zeta_time'))
            zeta_time.long_name = 'time for sea surface height'
            zeta_time.units = 'day'
            zeta_time.calendar = '360.0 days in every year'
            zeta_time.cycle_length = float(config.get('cycle'))

        if config.get('PISCES') == 'T':
            if config.get('DIC')[0] == 'Y': 
                dic_time = nc.createVariable('dic_time', 'f8', dimensions=('dic_time'))
                dic_time.long_name = 'time for DIC climatology'
                dic_time.units = 'day'
                dic_time.cycle_length = float(config.get('cycle'))

            if config.get('TALK')[0] == 'Y':
                talk_time = nc.createVariable('talk_time', 'f8', dimensions=('talk_time'))
                talk_time.long_name = 'time for TALK climatology'
                talk_time.units = 'day'
                talk_time.cycle_length = float(config.get('cycle'))

            if config.get('NO3')[0] == 'Y':
                no3_time = nc.createVariable('no3_time', 'f8', dimensions=('no3_time'))
                no3_time.long_name = 'time for NO3 climatology'
                no3_time.units = 'day'
                no3_time.cycle_length = float(config.get('cycle'))

            if config.get('NH4')[0] == 'Y':
                nh4_time = nc.createVariable('nh4_time', 'f8', dimensions=('nh4_time'))
                nh4_time.long_name = 'time for NH4 climatology'
                nh4_time.units = 'day'
                nh4_time.cycle_length = float(config.get('cycle'))

            if config.get('PO4')[0] == 'Y':
                po4_time = nc.createVariable('po4_time', 'f8', dimensions=('po4_time'))
                po4_time.long_name = 'time for PO4 climatology'
                po4_time.units = 'day'
                po4_time.cycle_length = float(config.get('cycle'))

            if config.get('Si')[0] == 'Y':
                si_time = nc.createVariable('si_time', 'f8', dimensions=('si_time'))
                si_time.long_name = 'time for SI climatology'
                si_time.units = 'day'
                si_time.cycle_length = float(config.get('cycle'))

            if config.get('FER')[0] == 'Y':
                fer_time = nc.createVariable('fer_time', 'f8', dimensions=('fer_time'))
                fer_time.long_name = 'time for FER climatology'
                fer_time.units = 'day'
                fer_time.cycle_length = float(config.get('cycle'))

            if config.get('O2')[0] == 'Y':
                o2_time = nc.createVariable('o2_time', 'f8', dimensions=('o2_time'))
                o2_time.long_name = 'time for O2 climatology'
                o2_time.units = 'day'
                o2_time.cycle_length = float(config.get('cycle'))

        if OpenBoundaries[0]: # South
            if config.get('temp')[0] == 'Y':
                temp_south = nc.createVariable('temp_south', 'f8', dimensions=('temp_time', 's_rho', 'xi_rho'), fill_value=0.)
                temp_south.long_name = 'southern boundary potential temperature'
                temp_south.units = 'Celsius'
                temp_south.coordinates = 'lon_rho s_rho temp_time'

            if config.get('salt')[0] == 'Y': 
                salt_south = nc.createVariable('salt_south', 'f8', dimensions=('salt_time', 's_rho', 'xi_rho'), fill_value=0.)
                salt_south.long_name = 'southern boundary salinity'
                salt_south.units = 'PSU'
                salt_south.coordinates = 'lon_rho s_rho salt_time'

            if config.get('PISCES') == 'T':
                if config.get('DIC')[0] == 'Y': 
                    DIC_south = nc.createVariable('DIC_south', 'f8', dimensions=('dic_time', 's_rho', 'xi_rho'), fill_value=0.)
                    DIC_south.long_name = 'southern boundary DIC'
                    DIC_south.units = 'mMol N m-3'

                if config.get('TALK')[0] == 'Y':
                    TALK_south = nc.createVariable('TALK_south', 'f8', dimensions=('talk_time', 's_rho', 'xi_rho'), fill_value=0.)
                    TALK_south.long_name = 'southern boundary TALK'
                    TALK_south.units = 'mMol N m-3'

                if config.get('NO3')[0] == 'Y':
                    NO3_south = nc.createVariable('NO3_south', 'f8', dimensions=('no3_time', 's_rho', 'xi_rho'), fill_value=0.)
                    NO3_south.long_name = 'southern boundary NO3'
                    NO3_south.units = 'mMol N m-3'

                if config.get('NH4')[0] == 'Y':
                    NH4_south = nc.createVariable('NH4_south', 'f8', dimensions=('nh4_time', 's_rho', 'xi_rho'), fill_value=0.)
                    NH4_south.long_name = 'southern boundary NH4'
                    NH4_south.units = 'mMol N m-3'

                if config.get('PO4')[0] == 'Y':
                    PO4_south = nc.createVariable('PO4_south', 'f8', dimensions=('po4_time', 's_rho', 'xi_rho'), fill_value=0.)
                    PO4_south.long_name = 'southern boundary PO4'
                    PO4_south.units = 'mMol N m-3'

                if config.get('Si')[0] == 'Y':
                    Si_south = nc.createVariable('Si_south', 'f8', dimensions=('si_time', 's_rho', 'xi_rho'), fill_value=0.)
                    Si_south.long_name = 'southern boundary Si'
                    Si_south.units = 'mMol N m-3'

                if config.get('FER')[0] == 'Y':
                    FER_south = nc.createVariable('FER_south', 'f8', dimensions=('fer_time', 's_rho', 'xi_rho'), fill_value=0.)
                    FER_south.long_name = 'southern boundary FER'
                    FER_south.units = 'mMol N m-3'

                if config.get('O2')[0] == 'Y':
                    O2_south = nc.createVariable('O2_south', 'f8', dimensions=('o2_time', 's_rho', 'xi_rho'), fill_value=0.)
                    O2_south.long_name = 'southern boundary O2'
                    O2_south.units = 'mMol N m-3'

            if config.get('u')[0] == 'Y':
                u_south = nc.createVariable('u_south', 'f8', dimensions=('v3d_time', 's_rho', 'xi_u'), fill_value=0.)
                u_south.long_name = 'southern boundary u-momentum component'
                u_south.units = 'meter second-1'
                u_south.coordinates = 'lon_u s_rho uclm_time'

            if config.get('v')[0] == 'Y':
                v_south = nc.createVariable('v_south', 'f8', dimensions=('v3d_time', 's_rho', 'xi_rho'), fill_value=0.)
                v_south.long_name = 'southern boundary v-momentum component'
                v_south.units = 'meter second-1'
                v_south.coordinates = 'lon_v s_rho vclm_time'

            if config.get('ubar')[0] == 'Y':
                ubar_south = nc.createVariable('ubar_south', 'f8', dimensions=('v2d_time', 'xi_u'), fill_value=0.)
                ubar_south.long_name = 'southern boundary vertically integrated u-momentum component'
                ubar_south.units = 'meter second-1'
                ubar_south.coordinates = 'lon_u uclm_time'

            if config.get('vbar')[0] == 'Y':
                vbar_south = nc.createVariable('vbar_south', 'f8', dimensions=('v2d_time', 'xi_rho'), fill_value=0.)
                vbar_south.long_name = 'southern boundary vertically integrated v-momentum component'
                vbar_south.units = 'meter second-1'
                vbar_south.coordinates = 'lon_v vclm_time'
            
            if config.get('zeta')[0] == 'Y':
                zeta_south = nc.createVariable('zeta_south', 'f8', dimensions=('zeta_time', 'xi_rho'), fill_value=0.)
                zeta_south.long_name = 'southern boundary sea surface height'
                zeta_south.units = 'meter'
                zeta_south.coordinates = 'lon_rho zeta_time'

        if OpenBoundaries[1]: #East 
            if config.get('temp')[0] == 'Y':
                temp_east = nc.createVariable('temp_east', 'f8', dimensions=('temp_time', 's_rho', 'eta_rho'), fill_value=0.)
                temp_east.long_name = 'eastern boundary potential temperature'
                temp_east.units = 'Celsius'
                temp_east.coordinates = 'lat_rho s_rho temp_time'

            if config.get('salt')[0] == 'Y':
                salt_east = nc.createVariable('salt_east', 'f8', dimensions=('salt_time', 's_rho', 'eta_rho'), fill_value=0.)
                salt_east.long_name = 'eastern boundary salinity'
                salt_east.units = 'PSU'
                salt_east.coordinates = 'lat_rho s_rho salt_time'

            if config.get('PISCES') == 'T':
                if config.get('DIC')[0] == 'Y': 
                    DIC_east = nc.createVariable('DIC_east', 'f8', dimensions=('dic_time', 's_rho', 'eta_rho'), fill_value=0.)
                    DIC_east.long_name = 'eastern boundary DIC'
                    DIC_east.units = 'mMol N m-3'

                if config.get('TALK')[0] == 'Y':
                    TALK_east = nc.createVariable('TALK_east', 'f8', dimensions=('talk_time', 's_rho', 'eta_rho'), fill_value=0.)
                    TALK_east.long_name = 'eastern boundary TALK'
                    TALK_east.units = 'mMol N m-3'

                if config.get('NO3')[0] == 'Y':
                    NO3_east = nc.createVariable('NO3_east', 'f8', dimensions=('no3_time', 's_rho', 'eta_rho'), fill_value=0.)
                    NO3_east.long_name = 'eastern boundary NO3'
                    NO3_east.units = 'mMol N m-3'

                if config.get('NH4')[0] == 'Y':
                    NH4_east = nc.createVariable('NH4_east', 'f8', dimensions=('nh4_time', 's_rho', 'eta_rho'), fill_value=0.)
                    NH4_east.long_name = 'eastern boundary NH4'
                    NH4_east.units = 'mMol N m-3'

                if config.get('PO4')[0] == 'Y':
                    PO4_east = nc.createVariable('PO4_east', 'f8', dimensions=('po4_time', 's_rho', 'eta_rho'), fill_value=0.)
                    PO4_east.long_name = 'eastern boundary PO4'
                    PO4_east.units = 'mMol N m-3'

                if config.get('Si')[0] == 'Y':
                    Si_east = nc.createVariable('Si_east', 'f8', dimensions=('si_time', 's_rho', 'eta_rho'), fill_value=0.)
                    Si_east.long_name = 'eastern boundary Si'
                    Si_east.units = 'mMol N m-3'

                if config.get('FER')[0] == 'Y':
                    FER_east = nc.createVariable('FER_east', 'f8', dimensions=('fer_time', 's_rho', 'eta_rho'), fill_value=0.)
                    FER_east.long_name = 'eastern boundary FER'
                    FER_east.units = 'mMol N m-3'

                if config.get('O2')[0] == 'Y':
                    O2_east = nc.createVariable('O2_east', 'f8', dimensions=('o2_time', 's_rho', 'eta_rho'), fill_value=0.)
                    O2_east.long_name = 'eastern boundary O2'
                    O2_east.units = 'mMol N m-3'

            if config.get('u')[0] == 'Y':
                u_east = nc.createVariable('u_east', 'f8', dimensions=('v3d_time', 's_rho', 'eta_rho'), fill_value=0.)
                u_east.long_name = 'eastern boundary u-momentum component'
                u_east.units = 'meter second-1'
                u_east.coordinates = 'lat_u s_rho uclm_time'

            if config.get('v')[0] == 'Y':
                v_east = nc.createVariable('v_east', 'f8', dimensions=('v3d_time', 's_rho', 'eta_v'), fill_value=0.)
                v_east.long_name = 'eastern boundary v-momentum component'
                v_east.units = 'meter second-1'
                v_east.coordinates = 'lat_v s_rho vclm_time'

            if config.get('ubar')[0] == 'Y':
                ubar_east = nc.createVariable('ubar_east', 'f8', dimensions=('v2d_time', 'eta_rho'), fill_value=0.)
                ubar_east.long_name = 'eastern boundary vertically integrated u-momentum component'
                ubar_east.units = 'meter second-1'
                ubar_east.coordinates = 'lat_u uclm_time'

            if config.get('vbar')[0] == 'Y':
                vbar_east = nc.createVariable('vbar_east', 'f8', dimensions=('v2d_time', 'eta_v'), fill_value=0.)
                vbar_east.long_name = 'eastern boundary vertically integrated v-momentum component'
                vbar_east.units = 'meter second-1'
                vbar_east.coordinates = 'lat_v vclm_time'
            
            if config.get('zeta')[0] == 'Y':
                zeta_east = nc.createVariable('zeta_east', 'f8', dimensions=('zeta_time', 'eta_rho'), fill_value=0.)
                zeta_east.long_name = 'eastern boundary sea surface height'
                zeta_east.units = 'meter'
                zeta_east.coordinates = 'lat_rho zeta_time'

        if OpenBoundaries[2]: # North
            if config.get('temp')[0] == 'Y':
                temp_north = nc.createVariable('temp_north', 'f8', dimensions=('temp_time', 's_rho', 'xi_rho'), fill_value=0.)
                temp_north.long_name = 'northern boundary potential temperature'
                temp_north.units = 'Celsius'
                temp_north.coordinates = 'lon_rho s_rho temp_time'

            if config.get('salt')[0] == 'Y':
                salt_north = nc.createVariable('salt_north', 'f8', dimensions=('salt_time', 's_rho', 'xi_rho'), fill_value=0.)
                salt_north.long_name = 'northern boundary salinity'
                salt_north.units = 'PSU'
                salt_north.coordinates = 'lon_rho s_rho salt_time'

            if config.get('PISCES') == 'T':
                if config.get('DIC')[0] == 'Y': 
                    DIC_north = nc.createVariable('DIC_north', 'f8', dimensions=('dic_time', 's_rho', 'xi_rho'), fill_value=0.)
                    DIC_north.long_name = 'northern boundary DIC'
                    DIC_north.units = 'mMol N m-3'
                    
                if config.get('TALK')[0] == 'Y':
                    TALK_north = nc.createVariable('TALK_north', 'f8', dimensions=('talk_time', 's_rho', 'xi_rho'), fill_value=0.)
                    TALK_north.long_name = 'northern boundary TALK'
                    TALK_north.units = 'mMol N m-3'

                if config.get('NO3')[0] == 'Y':
                    NO3_north = nc.createVariable('NO3_north', 'f8', dimensions=('no3_time', 's_rho', 'xi_rho'), fill_value=0.)
                    NO3_north.long_name = 'northern boundary NO3'
                    NO3_north.units = 'mMol N m-3'

                if config.get('NH4')[0] == 'Y':
                    NH4_north = nc.createVariable('NH4_north', 'f8', dimensions=('nh4_time', 's_rho', 'xi_rho'), fill_value=0.)
                    NH4_north.long_name = 'northern boundary NH4'
                    NH4_north.units = 'mMol N m-3'

                if config.get('PO4')[0] == 'Y':
                    PO4_north = nc.createVariable('PO4_north', 'f8', dimensions=('po4_time', 's_rho', 'xi_rho'), fill_value=0.)
                    PO4_north.long_name = 'northern boundary PO4'
                    PO4_north.units = 'mMol N m-3'

                if config.get('Si')[0] == 'Y':
                    Si_north = nc.createVariable('Si_north', 'f8', dimensions=('si_time', 's_rho', 'xi_rho'), fill_value=0.)
                    Si_north.long_name = 'northern boundary Si'
                    Si_north.units = 'mMol N m-3'

                if config.get('FER')[0] == 'Y':
                    FER_north = nc.createVariable('FER_north', 'f8', dimensions=('fer_time', 's_rho', 'xi_rho'), fill_value=0.)
                    FER_north.long_name = 'northern boundary FER'
                    FER_north.units = 'mMol N m-3'

                if config.get('O2')[0] == 'Y':
                    O2_north = nc.createVariable('O2_north', 'f8', dimensions=('o2_time', 's_rho', 'xi_rho'), fill_value=0.)
                    O2_north.long_name = 'northern boundary O2'
                    O2_north.units = 'mMol N m-3'

            if config.get('u')[0] == 'Y':
                u_north = nc.createVariable('u_north', 'f8', dimensions=('v3d_time', 's_rho', 'xi_u'), fill_value=0.)
                u_north.long_name = 'northern boundary u-momentum component'
                u_north.units = 'meter second-1'
                u_north.coordinates = 'lon_u s_rho uclm_time'

            if config.get('v')[0] == 'Y':
                v_north = nc.createVariable('v_north', 'f8', dimensions=('v3d_time', 's_rho', 'xi_rho'), fill_value=0.)
                v_north.long_name = 'northern boundary v-momentum component'
                v_north.units = 'meter second-1'
                v_north.coordinates = 'lon_v s_rho vclm_time'

            if config.get('ubar')[0] == 'Y':
                ubar_north = nc.createVariable('ubar_north', 'f8', dimensions=('v2d_time', 'xi_u'), fill_value=0.)
                ubar_north.long_name = 'northern boundary vertically integrated u-momentum component'
                ubar_north.units = 'meter second-1'
                ubar_north.coordinates = 'lon_u uclm_time'

            if config.get('vbar')[0] == 'Y':
                vbar_north = nc.createVariable('vbar_north', 'f8', dimensions=('v2d_time', 'xi_rho'), fill_value=0.)
                vbar_north.long_name = 'northern boundary vertically integrated v-momentum component'
                vbar_north.units = 'meter second-1'
                vbar_north.coordinates = 'lon_v vclm_time'
            
            if config.get('zeta')[0] == 'Y':
                zeta_north = nc.createVariable('zeta_north', 'f8', dimensions=('zeta_time', 'xi_rho'), fill_value=0.)
                zeta_north.long_name = 'northern boundary sea surface height'
                zeta_north.units = 'meter'
                zeta_north.coordinates = 'lon_rho zeta_time'

        if OpenBoundaries[3]: # West 
            if config.get('temp')[0] == 'Y':
                temp_west = nc.createVariable('temp_west', 'f8', dimensions=('temp_time', 's_rho', 'eta_rho'), fill_value=0.)
                temp_west.long_name = 'western boundary potential temperature'
                temp_west.units = 'Celsius'
                temp_west.coordinates = 'lat_rho s_rho temp_time'

            if config.get('salt')[0] == 'Y':
                salt_west = nc.createVariable('salt_west', 'f8', dimensions=('salt_time', 's_rho', 'eta_rho'), fill_value=0.)
                salt_west.long_name = 'western boundary salinity'
                salt_west.units = 'PSU'
                salt_west.coordinates = 'lat_rho s_rho salt_time'

            if config.get('PISCES') == 'T':
                if config.get('DIC')[0] == 'Y': 
                    DIC_west = nc.createVariable('DIC_west', 'f8', dimensions=('dic_time', 's_rho', 'eta_rho'), fill_value=0.)
                    DIC_west.long_name = 'western boundary DIC'
                    DIC_west.units = 'mMol N m-3'
                   
                if config.get('TALK')[0] == 'Y':
                    TALK_west = nc.createVariable('TALK_west', 'f8', dimensions=('talk_time', 's_rho', 'eta_rho'), fill_value=0.)
                    TALK_west.long_name = 'western boundary TALK'
                    TALK_west.units = 'mMol N m-3'

                if config.get('NO3')[0] == 'Y':
                    NO3_west = nc.createVariable('NO3_west', 'f8', dimensions=('no3_time', 's_rho', 'eta_rho'), fill_value=0.)
                    NO3_west.long_name = 'western boundary NO3'
                    NO3_west.units = 'mMol N m-3'

                if config.get('NH4')[0] == 'Y':
                    NH4_west = nc.createVariable('NH4_west', 'f8', dimensions=('nh4_time', 's_rho', 'eta_rho'), fill_value=0.)
                    NH4_west.long_name = 'western boundary NH4'
                    NH4_west.units = 'mMol N m-3'

                if config.get('PO4')[0] == 'Y':
                    PO4_west = nc.createVariable('PO4_west', 'f8', dimensions=('po4_time', 's_rho', 'eta_rho'), fill_value=0.)
                    PO4_west.long_name = 'western boundary PO4'
                    PO4_west.units = 'mMol N m-3'

                if config.get('Si')[0] == 'Y':
                    Si_west = nc.createVariable('Si_west', 'f8', dimensions=('si_time', 's_rho', 'eta_rho'), fill_value=0.)
                    Si_west.long_name = 'western boundary Si'
                    Si_west.units = 'mMol N m-3'

                if config.get('FER')[0] == 'Y':
                    FER_west = nc.createVariable('FER_west', 'f8', dimensions=('fer_time', 's_rho', 'eta_rho'), fill_value=0.)
                    FER_west.long_name = 'western boundary FER'
                    FER_west.units = 'mMol N m-3'

                if config.get('O2')[0] == 'Y':
                    O2_west = nc.createVariable('O2_west', 'f8', dimensions=('o2_time', 's_rho', 'eta_rho'), fill_value=0.)
                    O2_west.long_name = 'western boundary O2'
                    O2_west.units = 'mMol N m-3'

            if config.get('u')[0] == 'Y':
                u_west = nc.createVariable('u_west', 'f8', dimensions=('v3d_time', 's_rho', 'eta_rho'), fill_value=0.)
                u_west.long_name = 'western boundary u-momentum component'
                u_west.units = 'meter second-1'
                u_west.coordinates = 'lat_u s_rho uclm_time'

            if config.get('v')[0] == 'Y':
                v_west = nc.createVariable('v_west', 'f8', dimensions=('v3d_time', 's_rho', 'eta_v'), fill_value=0.)
                v_west.long_name = 'western boundary v-momentum component'
                v_west.units = 'meter second-1'
                v_west.coordinates = 'lat_v s_rho vclm_time'

            if config.get('ubar')[0] == 'Y':
                ubar_west = nc.createVariable('ubar_west', 'f8', dimensions=('v2d_time', 'eta_rho'), fill_value=0.)
                ubar_west.long_name = 'western boundary vertically integrated u-momentum component'
                ubar_west.units = 'meter second-1'
                ubar_west.coordinates = 'lat_u uclm_time'

            if config.get('vbar')[0] == 'Y':
                vbar_west = nc.createVariable('vbar_west', 'f8', dimensions=('v2d_time', 'eta_v'), fill_value=0.)
                vbar_west.long_name = 'western boundary vertically integrated v-momentum component'
                vbar_west.units = 'meter second-1'
                vbar_west.coordinates = 'lat_v vclm_time'
            
            if config.get('zeta')[0] == 'Y':
                zeta_west = nc.createVariable('zeta_west', 'f8', dimensions=('zeta_time', 'eta_rho'), fill_value=0.)
                zeta_west.long_name = 'western boundary sea surface height'
                zeta_west.units = 'meter'
                zeta_west.coordinates = 'lat_rho zeta_time'

        ''' Get S-coordinate at RHO points '''
        [z_rho, Cs_rho, sc_rho] = scoord2z('r', 
                np.array([0]), np.array([100]), # Use some dummy values for sea level and batymetry
                float(config.get('theta_s')),
                float(config.get('theta_b')),
                int(config.get('N')),
                float(config.get('hc')),
                scoord=scoord)
            
        ''' Get S-coordinate at W points '''
        [z_W, Cs_W, sc_W] = scoord2z('w', 
                np.array([0]), np.array([100]), # Use some dummy values for sea level and batymetry
                float(config.get('theta_s')),
                float(config.get('theta_b')),
                int(config.get('N')),
                float(config.get('hc')),
                scoord=scoord)

        ''' Write variables into NetCDF '''
        spherical[:] = 'T'

        vtransform[:] = int(config.get('Vtransform'))
        vstretching[:] = 1
        tstart[:] = config.get('time')[0]
        tend[:] = config.get('time')[-1]
        theta_s[:] = float(config.get('theta_s'))
        theta_b[:] = float(config.get('theta_b'))
        Tcline[:] = float(config.get('hc'))
        hc[:] = float(config.get('hc'))

        sc_r[:] = sc_rho
        sc_w[:] = sc_W
        Cs_r[:] = Cs_rho
        Cs_w[:] = Cs_W

        if config.get('temp')[0] == 'Y':
            temp_time[:] = config.get('time')

        if config.get('salt')[0] == 'Y':
            salt_time[:] = config.get('time')

        if config.get('PISCES') == 'T':
            if config.get('DIC')[0] == 'Y': 
                dic_time[:] = pisces_time
                talk_time[:] = pisces_time
            if config.get('NO3')[0] == 'Y':
                no3_time[:] = pisces_time
            if config.get('NH4')[0] == 'Y':
                nh4_time[:] = pisces_time
            if config.get('PO4')[0] == 'Y':
                po4_time[:] = pisces_time
            if config.get('Si')[0] == 'Y':
                si_time[:] = pisces_time
            if config.get('FER')[0] == 'Y':
                fer_time[:] = pisces_time
            if config.get('O2')[0] == 'Y':
                o2_time[:] = pisces_time

        if config.get('ubar')[0] == 'Y' or config.get('vbar')[0] == 'Y':
            v2d_time[:] = config.get('time')
        if config.get('u')[0] == 'Y' or config.get('v')[0] == 'Y':
            v3d_time[:] = config.get('time')

        if config.get('zeta')[0] == 'Y':
            ssh_time[:] = config.get('time')
            zeta_time[:] = config.get('time')

        bry_time[:] = config.get('time')

    return abspath
