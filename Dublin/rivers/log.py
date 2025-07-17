from datetime import datetime
import logging

def now():
    return datetime.now().strftime('%Y-%b-%d %H:%M:%S')

def set_logger():
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename=f'/log/app.log',
            format='%(message)s',
            filemode='w',
            level=logging.INFO)
    return logger
