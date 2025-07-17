from datetime import date, datetime
import numpy as np
from math import floor
import os

from log import set_logger, now

logger = set_logger()

swget = "wget --no-proxy --no-check-certificate -t 200 --waitretry=100 --retry-connrefused -c "

def flat(l):
    ''' Flatten list of lists '''
    return [i for j in l for i in j]
    
def read_tide_state(file):
    ''' Read CSV of tidal states for water level to flow conversion '''
    
    LowTideTimes = [] # Times of low tide when river water level is less
                      # likely to be affected by the incoming sea water.
    
    with open(file, 'r') as f:
        f.readline() # Discard header
        
        for line in f.readlines():
            time, state, _ = line.split(',')
            
            if 'LOW' in state:
                LowTideTimes.append(datetime.strptime(time, '%Y-%m-%d %H:%M:%S'))
                
    return np.array(LowTideTimes)

def level2flow(config, name, time, level):
    ''' Use rating curves in CONFIG to determine flows from water level.
        Here, CONFIG are the configuration options specified in the 
        "config" file. NAME is the river name. TIME is CROCO time.
        LEVEL is water level. '''
    
    logger.info(f'{now()} Converting water level to flow for {name}')
    
    try:
        today = datetime.strptime(config.get('mydate'), '%Y%m%d')
    except ValueError:
        today = datetime.now()
        
    offset = datetime.strptime(config.get('offset'), '%Y%m%d')
    
    Now = (today - offset).total_seconds()/86400
    
    # Trim off the first and last day on the
    # assumption that these are "part days".
    w = np.where(np.logical_and(time >= 1 + np.floor(time[0]),
                                time < floor(Now)))
    
    time, level = time[w], level[w]
    
    Q = -np.ones_like(level)
    
    for i in range(10):
        try:
            # Rating curve found for this river. Get parameters
            parameters = config[f'{name.upper()}-{i}']
            
            # Get conversion shift to staff level
            staff = float(parameters[0])
            # Add shift
            level_i = level + staff
            
            # Get upper threshold for this rating curve
            threshold = float(parameters[1])
            # Find indexes where water level is below upper threshold
            w = np.where(level_i <= threshold)
            
            # Get "s" in "A * (S + s) ^ k"
            s = float(parameters[2])
            # Get "A" in "A * (S + s) ^ k"
            A = float(parameters[3])
            # Get "k" in "A * (S + s) ^ k"
            k = float(parameters[4])
            
            logger.info(f'{now()}   Using rating curve {A} * (S + {s}) ^ {k}')
            
            # Define rating curve 
            RatingCurve = lambda S : A *  (S + s) ** k
            # Calculate flow
            Q_i = RatingCurve(level_i)
            # Write into output array
            Q[w] = Q_i[w]
            
        except KeyError:
            break
        
    if np.any(Q < 0):
        raise RuntimeError('''Found negative flow. 
            Have you defined rating curves covering every water level intervals? 
                           ''')   
             
    ''' Get daily values based on tidal information '''
    tideFile = f'{name.upper()}' + '-TIDES.csv'
    if os.path.isfile(tideFile):
        logger.info(f'{now()} Reading tidal state for {name} from {tideFile}')
        LowTideTimes = read_tide_state(tideFile)
        
        # Convert tidal times to CROCO time (days since offset)
        LowTideTimes = np.array([(i - offset).total_seconds()/86400 
                                 for i in LowTideTimes])
        
        # Find tidal times within river time interval
        w = np.where(np.logical_and(LowTideTimes >= time[0],
                                    LowTideTimes <= time[-1]))        
        LowTideTimes = LowTideTimes[w]
        
        DT = float(parameters[5])/1440 # Time interval to search 
                                       # around low tide times
        
        timeLow, Qlow = [], [] # Find times and flows at low tide
        for i in LowTideTimes:
            w = np.where(np.logical_and(time >= i-DT,  # Search interval
                                        time <= i+DT)) # around low tide time
            # These are times around low tide
            timeLow.append(time[w].tolist())
            # These are calculated flows around low tide
            Qlow.append(Q[w].tolist())
        # Convert low-tide times and flows to NumPy arrays for convenience
        timeLow, Qlow = np.array(flat(timeLow)), np.array(flat(Qlow))
            
        # The output will be low-tide, daily-averaged flows, referenced at noon
        noon = np.array([floor(i) + .5 for i in timeLow]) # Noon times
        
        Qmean = [] # Initialize low-tide, daily-averaged flow array        
        for i in noon: # For ecach day
            w = np.where(np.logical_and(
                         timeLow >= i-.5, # Find indexes for this day, before noon
                         timeLow <  i+.5, # Find indexes for this day, after noon
                         Qlow > 0))       # Ignore invalid, negative flows, if any
            
            # There has to be at least six values to accept this as a valid average
            if len(w[0]) < 6: 
                raise RuntimeError(f'''{name}: The number of good points is 
                                   less than threshold for {i}''')
            else:
                Qmean.append(Qlow[w].mean()) # Append low-tide, daily-averaged flow
            
        time, Q = noon, np.array(Qmean)
        
    else:
        logger.info(f'{now()} {name}: Tidal state file not found! Corrections will not be applied')
    
    return time, Q
