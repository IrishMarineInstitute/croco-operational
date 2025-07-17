from datetime import date, timedelta
import traceback
import shutil

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

    # Get start and end dates for hindcast (in days relative to last midnight)
    HCi, HCe = float(config.get('HCi')), float(config.get('HCe'))
    # Get length of hindcast (days)
    hindcast_length = HCe - HCi

    # Get model time step [s]
    dt = float(config.get('timestep'))

    # Decide number of time steps
    ntimes = 86400 * hindcast_length / dt

    shutil.copy('template.in', 'croco.in')

    textrep('{NTIMES}', str(int(ntimes))); textrep('{DT}', str(int(dt)))

    idate = date.today() + timedelta(days=HCi)
    edate = date.today() + timedelta(days=HCe)

    textrep('{BYEAR}', idate.strftime('%Y'))
    #
    textrep('{BMONTH}', str(int(idate.strftime('%m'))))
    #
    textrep('{BYEAREND}', edate.strftime('%Y'))
    #
    textrep('{BMONTHEND}', str(int(edate.strftime('%m'))))

    with open('/log/input-hindcast.config', 'w') as f:
        f.write(f'date={idate.strftime("%Y%m%d")}')

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error("Exception in INPUT HC: " + str(e.args[0]))
        logger.error(traceback.format_exc())

