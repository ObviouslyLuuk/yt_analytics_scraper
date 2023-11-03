
import sys
import logging
import functools

import datetime as dt

class Tee(object):
    """
    Print to all files passed, for example console and a logfile.
    Can be used in place of sys.stdout.

    Usage:
    sys.stdout = Tee(sys.stdout, f)

    credit:
    https://stackoverflow.com/questions/17866724/python-logging-print-statements-while-having-them-print-to-stdout
    """
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
    def flush(self):
        pass


def get_logging_decorator(filename):
    """Return logging decorator that logs into <filename>.txt and logs errors into <filename>_error.log"""
    def logging_decorator(func):
        """Log errors from <func>"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Initialize logger
            logging.basicConfig(filename=filename+"_errors.log", level=logging.ERROR, 
                                format='%(asctime)s %(levelname)s %(name)s %(message)s')
            logging.getLogger(__name__)

            # Set stdout to both console and log file
            f = open(filename+".txt", 'a')
            sys.stdout = Tee(sys.stdout, f)
            print(f"\nDatetime: {dt.datetime.now()}")

            # Log any errors during execution of func
            try:
                return func(*args, **kwargs)
            except Exception as err:
                print("Error: ", err)
                logging.error(err)
                raise err
        return wrapper
    return logging_decorator