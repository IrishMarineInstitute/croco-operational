from datetime import date, datetime, timedelta
import traceback
import ftplib
import shutil
import glob
import time
import os

from log import set_logger, now

logger = set_logger()

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

def ecmwf_download():
    ''' Download ECMWF files as provided by MetEireann at the Marine Institute FTP site '''

    today = date.today(); yesterday = today - timedelta(days=1)
    # First, set up some useful date strings
    yearToday, dateToday = today.strftime('%Y'), today.strftime('%m%d')

    config = configuration()

    # Get FTP host, username and password
    host, user, pswd = config.get('ftphost'), config.get('ftpuser'), config.get('ftppswd')

    # Set output directory to save GRIB files
    metpath = config.get('metpath')
    if not os.path.isdir(metpath):
        os.makedirs(metpath)

    # Open FTP connection using the credentials provided
    ftp = ftplib.FTP(host, user, pswd)
    logger.info(f'{now()} FTP connection successfully established')
    # Enforce UTF-8 encoding
    ftp.encoding = "utf-8"
    # Get a list of GRIB files in the FTP server
    filenames = ftp.nlst()
    logger.info(f'{now()} There are {len(filenames)} files in FTP')

    # Use a counter to check that the number of downloaded files is correct
    C = 0

    logger.info(f'{now()} Starting download...')
    for name in filenames: # Loop along files
        if name[0:3] == 'IQS' or name[0:3] == 'IQD':
            with open(name, 'wb') as f:
                ftp.retrbinary(f'RETR {name}', f.write)
                logger.info(f'{now()} {name} Downloaded'); C += 1
    # Close FTP connection
    ftp.quit(); logger.info(f'{now()} FTP connection closed')

    ''' Hindcast files - IQS '''
    hindcastPath = metpath + 'HC/'
    # Set path for GRIB files
    gribPath = hindcastPath + 'GRIB/' + yearToday + '/'
    if not os.path.isdir(gribPath):
        os.makedirs(gribPath)

    today = datetime(today.year, today.month, today.day)
    for k in range(1, 25):
        time = today + timedelta(hours=k)
        date_k = time.strftime('%m%d%H')

        if k < 13:
            fname = 'IQS' + dateToday + '0000' + date_k + '001'
            movefile(fname, gribPath + fname.replace('IQS', 'IQS' + yearToday))
        else: # Some of these files are needed in forecast section below
            fname = 'IQS' + dateToday + '1200' + date_k + '001'
            copyfile(fname, gribPath + fname.replace('IQS', 'IQS' + yearToday))

    # Remove HC GRIB files older than ten days
    clean(gribPath, 10); 

    ''' Forecast files '''
    forecastPath = metpath + 'FC/'
    # Set path for GRIB files
    gribPath = forecastPath + 'GRIB/'
    if not os.path.isdir(gribPath):
        os.makedirs(gribPath)

    # Process ECMWF hourly files
    for k in range(1, 91):
        time = today + timedelta(hours=12) + timedelta(hours=k)
        date_k = time.strftime('%m%d%H')
        fname = 'IQS' + dateToday + '1200' + date_k + '001'
        movefile(fname, gribPath + fname.replace('IQS', 'IQS' + yearToday))

    # Process ECMWF 3-hourly files
    for k in range(93, 147, 3):
        time = today + timedelta(hours=12) + timedelta(hours=k)
        date_k = time.strftime('%m%d%H')
        fname = 'IQD' + dateToday + '1200' + date_k + '001'
        movefile(fname, gribPath + fname.replace('IQD', 'IQD' + yearToday))

    for k in range(3, 147, 3):
        time = today + timedelta(hours=12) + timedelta(hours=k)
        date_k = time.strftime('%m%d%H')
        fname = 'IQP' + dateToday + '1200' + date_k + '001'
        movefile(fname, gribPath + fname.replace('IQP', 'IQP' + yearToday))

    for k in range(150, 162, 6):
        time = today + timedelta(hours=12) + timedelta(hours=k)
        date_k = time.strftime('%m%d%H')
        fname = 'IQP' + dateToday + '1200' + date_k + '001'
        movefile(fname, gribPath + fname.replace('IQP', 'IQP' + yearToday))

    # Remove any files that are left over
    remainder = glob.glob('IQ*')
    for f in remainder:
        os.remove(f)

    # Remove FC GRIB files older than three days
    clean(gribPath, 3); 

    logger.info(f'{now()} Finished download'); logger.info(' ')

    # Check the number of downloaded files
    if C != 228:
        raise FileNotFoundError(f'Error in ECMWF: Expected to download 228 files from FTP, but {C} were downloaded instead')

def clean(path, D):
    ''' Removes files in path older than D days '''
    old = time.time() - D * 86400
    for f in os.listdir(path):
        file = os.path.join(path, f)
        if os.path.isfile(file):
            if os.path.getctime(file) < old:
                os.remove(file)

def movefile(source, destination):
    if os.path.isfile(source):
        shutil.move(source, destination)

def copyfile(source, destination):
    if os.path.isfile(source):
        shutil.copy(source, destination)

if __name__ == '__main__':
    try:
        ecmwf_download()
    except Exception as e:
        logger.error("Exception in ECMWF Data Download: " + str(e.args[0]))
        logger.error(traceback.format_exc())

