# Selenium stuff
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.chrome.options import Options
from .chromedriver_manager import ChromeDriverManager # my own adaptation of webdriver_manager

from send_email.send_email import send_email

from .custom_values import CHROMEDRIVER_PATH, USER_DATA_PATH, CHROME_PROFILE, USER_DATA_BACKUP_PATH, CHANNEL_ID
from .constants import VIDEOS_URL

# Folder manipulation stuff
from shutil import rmtree
from distutils.dir_util import copy_tree

# For decorator
import sys
import logging
import functools
import datetime as dt

def startWebdriver(chromedriver_path="manager", use_profile=CHROME_PROFILE, printing=False) -> webdriver.Chrome:
    """Starts the selenium webdriver and adds options"""

    chrome_options = Options()
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    if use_profile:
        # The CHROME_PROFILE is a folder in the USER_DATA_PATH
        chrome_options.add_argument("user-data-dir="+USER_DATA_PATH)
        chrome_options.add_argument("profile-directory="+CHROME_PROFILE)
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("disable-infobars")
    chrome_options.binary_location = "C:\Program Files\Google\Chrome Beta\Application\chrome.exe"

    if chromedriver_path == "manager":
        manager = ChromeDriverManager()
        if printing:
            # print("OS Type: " + manager.get_os_type())
            # print("Browser type: ", manager.driver.get_browser_type())
            print("Browser version: ", manager.driver.get_browser_version_from_os())
            print("Latest driver: ", manager.driver.get_latest_release_version())
            print("Driver download url: ", manager.driver.get_driver_download_url(manager.get_os_type()))
        chromedriver_path = ChromeDriverManager().install()

    return webdriver.Chrome(chromedriver_path, options=chrome_options)

def replace_dir(dir, replace_dir):
    """Remove <dir> folder and replace it with <replace_dir> folder."""
    rmtree(dir)
    copy_tree(replace_dir, dir)

def reset_user_data(dir=USER_DATA_PATH, replace_dir=USER_DATA_BACKUP_PATH):
    """
    Remove <dir> folder and replace it with <replace_dir> folder.
    Appears to fix the problem where the chromedriver stops working after a while.
    The error was:
    selenium.common.exceptions.WebDriverException: Message: unknown error: cannot parse internal JSON template: Line: 1, column: 1, Unexpected token.
    """
    replace_dir(dir, replace_dir)
    print(f"Reset User Data for webdriver [{__file__}]")


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


def test_YouTube_login(driver, email=False, printing=False):
    """Raise AssertionError if the driver is on the sign in page. If email is True, send an email notification. 
    If printing is True, print the attempted url and the current url."""
    url = VIDEOS_URL.format(channel_id=CHANNEL_ID, upload_or_live="live")
    driver.get(url)
    if printing:
        print("attempted url: ", url)
        print("current url: ", driver.current_url)

    try:
        assert "signin" not in driver.current_url, "Sign in page, YouTube login test failed"
    except AssertionError as e:
        if email:
            send_email("YouTube login test failed", "Sign in page, YouTube login test failed.")
        raise e


def catch_user_data_error(func):
    """If the WebDriverException happens, calls the reset_user_data function and tries again."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TimeoutException as e: # TimeoutException is a subclass of WebDriverException so must be first
            raise TimeoutException(f"{e}\nTimeout, so potentially a login issue")
        except WebDriverException as e:
            print("WebDriverException ", e)
            print(f"resetting user data [{__file__}]")
            reset_user_data()
            return func(*args, **kwargs)
    return wrapper


def extract_from_str(str, pre_str, post_str):
    """Return string between pre_str and post_str in str"""
    # Find pre string in html
    start = str.find(pre_str)
    str = str[start+len(pre_str):]
    # Find post string in title and return
    return str[:str.find(post_str)]


def wait_for_element(driver, css, timeout=10):
    """Wait for element to appear on page"""
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
