# Selenium stuff
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options

from .custom_values import CHROMEDRIVER_PATH, USER_DATA_PATH, CHROME_PROFILE, USER_DATA_BACKUP_PATH

# Folder manipulation stuff
from shutil import rmtree
from distutils.dir_util import copy_tree

# For decorator
import sys
import logging
import functools
import datetime as dt

def startWebdriver() -> webdriver.Chrome:
    """Starts the selenium webdriver and adds options"""

    chrome_options = Options()
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-data-dir="+USER_DATA_PATH)
    chrome_options.add_argument("profile-directory="+CHROME_PROFILE)
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("disable-infobars")

    return webdriver.Chrome(CHROMEDRIVER_PATH, options=chrome_options)


def reset_user_data(dir, replace_dir):
    """
    Remove <dir> folder and replace it with <replace_dir> folder.
    Appears to fix the problem where the chromedriver stops working after a while.
    The error was:
    selenium.common.exceptions.WebDriverException: Message: unknown error: cannot parse internal JSON template: Line: 1, column: 1, Unexpected token.
    """
    rmtree(dir)
    copy_tree(replace_dir, dir)
    print("Reset User Data for webdriver")


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
                logging.error(err)
        return wrapper
    return logging_decorator


def catch_user_data_error(func):
    """If the WebDriverException happens, calls the reset_user_data function and tries again."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except WebDriverException:
            reset_user_data(USER_DATA_PATH, USER_DATA_BACKUP_PATH)
            return func(*args, **kwargs)
    return wrapper
