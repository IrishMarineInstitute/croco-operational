from datetime import datetime
from io import StringIO
import numpy as np
import pdfplumber
import json

def read_json(file):
    ''' Read JSON file as downloaded from OPW '''
    
    with open(file, 'r') as f:
        io = StringIO(f.readline())
    # Load JSON structure    
    OPW = json.load(io)[0]

    data = OPW.get('data')
    
    # Output initialization (time and river flow)
    time, flow = [], []
    
    for i in data: # Loop along data
        t, Q, _ = i
        # Append time
        time.append(datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.000Z'))
        # Append flow
        try:
            flow.append(float(Q))
        except TypeError:
            flow.append(np.nan)

    try:
        assert(len(time) == len(flow))
    except AssertionError:
        raise AssertionError('River time and flow have different lengths')

    return np.array(time), np.array(flow), OPW.get('stationparameter_name')[0]

def read_csv(file):
    ''' Read CSV file as downloaded from EPA '''

    # Output initialization (time and river flow)
    time, flow = [], []

    with open(file, 'r') as f:
        for line in f.readlines():
            try:
                t, Q, _ = line.split(';')

                # Append flow
                try:
                    flow.append(float(Q))
                except TypeError:
                    flow.append(np.nan)

                # Append time
                time.append(datetime.strptime(t, '%Y-%m-%d %H:%M:%S'))

            except ValueError:
                if 'Parameter' in line:
                    if 'River Discharge' in line:
                        parameter = 'Q'
                    elif 'Stage' in line:
                        parameter = 'S'
                    else:
                        raise RuntimeError('Unexpected EPA parameter')

    try:
        assert(len(time) == len(flow))
    except AssertionError:
        raise AssertionError('River time and flow have different lengths')

    return np.array(time), np.array(flow), parameter

def read_pdf(file):
    ''' Read PDF file as downloaded from ESB '''

    # Output initialization (time and river flow)
    time, flow = [], []

    with pdfplumber.open(file) as pdf:
        page = pdf.pages[1] # ESB table in 2nd page
        #  Read text in page
        text = page.extract_text()

    lines = text.split('\n') # Split by lines
    for i in lines:
        words = i.split(' ')
        try:
            # Read ESB date
            date = datetime.strptime(words[0], '%d-%b-%y')
            # Read ESB time
            t = datetime.strptime(words[1], '%H:%M:%S')
            # Append time
            time.append(datetime(date.year, date.month, date.day,
                t.hour, t.minute, t.second))
            # Append flow (m3/s)
            flow.append(float(words[2]))
        except ValueError:
            continue

    try:
        assert(len(time) == len(flow))
    except AssertionError:
        raise AssertionError('River time and flow have different lengths')

    return np.flip(np.array(time)), np.flip(np.array(flow)), 'Q' # ESB is always 'Q'

