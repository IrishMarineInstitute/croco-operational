from datetime import date, timedelta
import traceback
import shutil
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

def textrep(old, new):
    ''' Replace in croco.in string "OLD" with string "NEW" '''

    with open('croco.in', 'r') as f:
        data = f.read()
        # Replace text
        data = data.replace(old, new)

    with open('croco.in', 'w') as f:
        f.write(data)

def main():
    ''' Create croco.in for this FC run '''

    config = configuration()
    
    # Get start and end dates for forecast (in days relative to last midnight)
    FCi, FCe = float(config.get('FCi')), float(config.get('FCe'))
    # Get length of forecast (days)
    forecast_length = FCe - FCi

    # Get model time step [s]
    dt = float(config.get('timestep'))

    # Decide number of time steps
    if date.today().strftime('%a') == config.get('HCwd'):
        # Today is hindcast day, and therefore forecast catch-up run!
        # Tonight's forecast run will be +2 days longer, since it will be
        # restarted from today's hindcast last time step.
        ntimes = 86400 * (forecast_length + 2) / dt

    else:
        # Tonight's will be a regular forecast run
        ntimes = 86400 * forecast_length / dt

    shutil.copy('template.in', 'croco.in')

    textrep('{NTIMES}', str(int(ntimes))); textrep('{DT}', str(int(dt)))

    idate = date.today() + timedelta(days=FCi)
    edate = date.today() + timedelta(days=FCe)

    textrep('{BYEAR}', idate.strftime('%Y'))
    #
    textrep('{BMONTH}', str(int(idate.strftime('%m'))))
    #
    textrep('{BYEAREND}', edate.strftime('%Y'))
    #
    textrep('{BMONTHEND}', str(int(edate.strftime('%m'))))

    delete_empty_folders('/data') # Clean containers filesystem

def delete_empty_folders(root):
    ''' This function is taken from Question 47093561 on Stackoverflow.
    The objective is to remove any empty directories left in the 
    containers filesystem. This job could be carried out by any other
    container. '''

    deleted = set()

    for current_dir, subdirs, files in os.walk(root, topdown=False):

        still_has_subdirs = False
        for subdir in subdirs:
            if os.path.join(current_dir, subdir) not in deleted:
                still_has_subdirs = True
                break

        if not any(files) and not still_has_subdirs:
            os.rmdir(current_dir)
            deleted.add(current_dir)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error("Exception in INPUT FC: " + str(e.args[0]))
        logger.error(traceback.format_exc())

