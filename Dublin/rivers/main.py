from create_runoff_file import create_runoff
from datetime import date, datetime, timedelta
from level2flow import level2flow
from log import set_logger, now
from subprocess import call
from netCDF4 import Dataset
import readers as R
import numpy as np
import traceback
import archive
import glob
import time
import os

logger = set_logger()

swget = "wget --no-proxy --no-check-certificate -t 200 --waitretry=100 --retry-connrefused -c "

nutrients = ('NO3', 'PO4', 'Si', 'FER')

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

def L(msg):
    ''' Log message '''
    logger.info(f'{now()} {msg}')

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
    edate = today + timedelta(days=int(config.get('days-ahead'))+1+30) # 16/07/2025. After EPA server failure
                                         # a drastic solution: extend time array by 30 days to be
                                         # covered in case of similar errors in the future. The latest measure
                                         # is repeated.
    edatestr = edate.strftime('%Y%m%d')

    return idate, idatestr, edate, edatestr

def oxygen_solubility(T):
    ''' https://doi.org/10.1016/S0304-386X(98)00007-3 '''

    return 210000*np.exp((0.046*T**2+203.357*T*np.log(T/298)-(299.378+0.092*T)*(T-298)-20591)/(8.3144*T))

def opw(config):
    ''' Download river flows from Office of Public Works '''

    shttpOPW = "https://waterlevel.ie/hydro-data/data/internet/stations/0/"

    localpath = config.get('riverspath') # Local path to download files to

    for i in range(1000):
        try:
            river = config[f'OPW-{i:03d}'] # Get OPW station number
        except KeyError:
            break # No more OPW stations to download. Exit loop

        L(f'Downloading OPW-{i:03d}...')

        # Determine whether flow (Q) or water level (S) will be downloaded
        if river[1] == "Q":
            string = shttpOPW + river[0] + "/Q/month.json" # Download flow
        elif river[1] == "S":
            string = shttpOPW + river[0] + "/S/month.json" # Download water level
        elif river[1] == "T":
            string = shttpOPW + river[0] + "/TWater/month.json" # Download water level
        else:
            raise TypeError(f"""Error downloading OPW-{i:03d}: data source must be
                either 'Q' (flow), 'S' (water level) or 'T' (temperature) """)

        call([swget + string], shell=True) # Download 

        call(['mv month.json ' + localpath + '/' + f'OPW-{i:03d}' + '.json'],
                shell=True) # Move to local path

def epa(config):
    ''' Download river flows from Environmental Protection Agency '''

    shttpEPA = "https://epawebapp.epa.ie/Hydronet/output/internet/stations/"
    
    localpath = config.get('riverspath') # Local path to download files to

    for i in range(1000):
        try:
            river = config[f'EPA-{i:03d}'] # Get EPA station number
        except KeyError:
            break # No more EPA stations to download. Exit loop

        L(f'Downloading EPA-{i:03d}...')

        # Determine whether flow (Q) or water level (S) will be downloaded
        if river[1] == "Q":
            string = shttpEPA + river[0] + "/Q/3_months.zip" # Download flow
        elif river[1] == "S":
            string = shttpEPA + river[0] + "/S/3_months.zip" # Download water level
        else:
            raise TypeError(f"""Error downloading EPA-{i:03d}: data source must be
                either 'Q' (flow) or 'S' (water level) """)

        call([swget + string], shell=True) # Download

        call(['unzip', '3_months.zip']) # Unzip and release CSV
        call(['rm', '3_months.zip'])    # Remove zip

        call(['mv 3_months.csv ' + localpath + '/' + f'EPA-{i:03d}' + '.csv'],
                shell=True) # Move to local path

def esb(config):
    ''' Download river flows from Electricity Supply Board '''

    swget = "wget --no-proxy -t 200 --waitretry=100 --retry-connrefused -c -O "

    shttpESB = "http://www.esbhydro.ie/"

    localpath = config.get('riverspath')

    for i in range(1000):
        try:
            river = config[f'ESB-{i:03d}']
        except KeyError:
            break # No more ESB stations to download. Exit loop

        L(f'Downloading ESB-{i:03d}...')

        string = localpath + '/' + f'ESB-{i:03d}' + '.pdf ' + shttpESB + river

        call([swget + string], shell=True) # Download

def river_download():
    ''' Download river data from OPW, ESB, EPA '''

    config = configuration()

    ''' Set output directory before download '''
    localpath = config.get('riverspath')
    if not os.path.isdir(localpath):
        os.makedirs(localpath)
    # Clean directory
    files = glob.glob(f'{localpath}/*')
    for f in files:
        os.remove(f)

    # Download river data
    opw(config); epa(config); esb(config)

def make_runoff():
    ''' Create CROCO runoff forcing file '''

    config = configuration()

    # Get reference offset time for CROCO
    offset = datetime.strptime(config.get('offset'), '%Y%m%d')

    idate, idatestr, edate, edatestr = get_dates(config)

    # Set time step for river time as 15 minutes
    DT = timedelta(minutes=15)

    # Make sure time is an array of datetime objects
    time = np.append(np.arange(idate, edate, DT),
            datetime.combine(edate, datetime.min.time()))
    # Convert to days since offset time 
    time = np.array([(i - offset).total_seconds()/86400 for i in time])
    # Add time to general setup to define boundary forcing file time dimension
    config['time'] = time 
    # Use today as current date, unless selected otherwise
    try:
        today = datetime.strptime(config.get('mydate'), '%Y%m%d')
    except ValueError:
        today = date.today()

    riverspath = config.get('riverspath')

    # Remove NetCDF files older than 2 days
    clean(config.get('hindpath') + '/', 2)

    localpath = config.get('hindpath') + '/' + today.strftime('%Y%m%d') + '/'
    if not os.path.isdir(localpath):
        os.makedirs(localpath)
    config['localpath'] = localpath

    # Create runoff forcing file
    L('Creating runoff file...'); cdf = create_runoff(config)

    if not cdf:
        L('Number of rivers is 0. Nothing to do'); return

    for i in range(1000):
        try:
            river = config[f'RIVER-{i:03d}']
            # Get river name and number of CROCO grid cells for this river
            name, n = river[0], int(river[5])

            L(' '); L(f'Processing {name}')
           
            # Initialize flow for this river
            QBAR = np.zeros(len(time))
            
            boolQ, boolT = False, False
            
            # Search datasets for this rivers
            for j in river:
                if ('OPW-' in j) or ('EPA-' in j) or ('ESB-' in j):
                    try:
                        f = glob.glob(f'{riverspath}/{j}.*')[0]
                    except IndexError:
                        raise IndexError(f'Could not find dataset {j} for river {name}')

                    L(f'    Found dataset {f}')

                    if f[-3::] == 'son': # JSON file (OPW)
                        t, Q, param = R.read_json(f); Q = Q * 1/n
                    elif f[-3::] == 'csv': # CSV file (EPA)
                        t, Q, param = R.read_csv(f);  Q = Q * 1/n
                    elif f[-3::] == 'pdf': # PDF file (ESB)
                        t, Q, param = R.read_pdf(f);  Q = Q * 1/n
                    else:
                        raise RuntimeError('Unrecognized river file')

                    L('    Read successfully')

                    # Convert river time to days since CROCO offset
                    t = np.array([(i - offset).total_seconds()/86400 for i in t])

                    if param == "T":
                        # Perform 1-D interpolation to CROCO time
                        TRIV = np.interp(time, t, Q); boolT = True; continue

                    if param == "S":
                        # Use rating curves to calculate flow from water level
                        t, Q = level2flow(config, name, t, Q)

                    # Perform 1-D interpolation to CROCO time
                    QBAR = QBAR + np.interp(time, t, Q); boolQ = True 

                elif 'CON-' in  j: # Constant flow
                    QBAR = QBAR + float(config[j]); boolQ = True


            if not boolT:
                raise FileNotFoundError(f'Could not find temperature for {name}')
            if not boolQ:
                raise FileNotFoundError(f'Could not find flow for {name}')

            # Update archive
            L(f'   Updating archive for {name}')
            archive.update_river_archive(config, name, time, n*QBAR, TRIV)

            L('   Writing into CROCO_RUNOFF.nc')
            with Dataset(cdf, 'a') as nc:
                nc.variables['Qbar'][i,:] = QBAR     # Write flows
                nc.variables['temp_src'][i,:] = TRIV # Write temperature
                if config.get('PISCES') == 'T':
                    nc.variables['O2_src'][i,:] = oxygen_solubility(TRIV + 273.15) # Write oxygen

            if config.get('PISCES') == 'T':
                for X in nutrients:
                    if f'{name}-{X}' in config:
                        expfit = config.get(f'{name}-{X}') # Get exponential fit parameters
                        A, k = float(expfit[0]), float(expfit[1])
                        with Dataset(cdf, 'a') as nc:
                            L(f'      Writing {name}-{X} to {X}_src using A = {A}, k = {k}')
                            nc.variables[f'{X}_src'][i,:] = A * QBAR ** (k+1) # Calculate concentration

        except KeyError:
            break # No more rivers to process. Exit loop

    with open('/log/rivers.config', 'w') as f:
        f.write(f'runoffname={os.path.abspath(cdf)}')
    
    L('END')

def clean(path, D):
    ''' Removes files in path older than D days '''
    old = time.time() - D * 86400
    for f in glob.glob(path + '**/croco_runoff.nc', recursive=True):
        file = os.path.abspath(f)
        if os.path.getctime(file) < old:
            logger.info(f'{now()} Deleting {file}') 
            os.remove(file)

if __name__ == '__main__':
    ''' PART 1: Download river '''
    try:
        river_download()
    except Exception as e:
        logger.error("Exception in River Download: " + e.args[0])
        logger.error(traceback.format_exc())

    L(' ')

    ''' PART 2: Create CROCO runoff NetCDF '''
    try:
        make_runoff()
    except Exception as e:
        logger.error("Exception while creating runoff forcing: " + e.args[0])
        logger.error(traceback.format_exc())
