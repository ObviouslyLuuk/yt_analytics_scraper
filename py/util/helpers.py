# Selenium stuff
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from .custom_values import CHROMEDRIVER_PATH, CHROME_PROFILES, CHROME_PROFILE

# Folder manipulation stuff
from shutil import rmtree
from distutils.dir_util import copy_tree

def startWebdriver() -> webdriver.Chrome:
    """Starts the selenium webdriver and adds options"""

    chrome_options = Options()
    # chrome_options.add_argument("--no-sandbox") # Bypass OS security model

    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-data-dir="+CHROME_PROFILES)
    chrome_options.add_argument("profile-directory="+CHROME_PROFILE)
    # chrome_options.add_argument("--window-size=10,10")
    chrome_options.add_argument("--start-maximized")

    # chrome_options.add_argument("--disable-dev-shm-usage") # https://stackoverflow.com/questions/50642308/webdriverexception-unknown-error-devtoolsactiveport-file-doesnt-exist-while-t
    chrome_options.add_argument("disable-infobars") # disabling infobars

    return webdriver.Chrome(CHROMEDRIVER_PATH, options=chrome_options)


def reset_user_data(dir, replace_dir):
    """
    Remove <dir> folder and replace it with <replace_dir> folder.
    Appears to fix the problem where the chromedriver stops working after a while.
    The error was:

    Traceback (most recent call last):
  File "d:/Users/Luuk/Documents/Programming/PersonalProjects/yt_analytics_scraper/py/test.py", line 27, in <module>
    driver = startWebdriver()
  File "d:/Users/Luuk/Documents/Programming/PersonalProjects/yt_analytics_scraper/py/test.py", line 24, in startWebdriver
    return webdriver.Chrome(CHROMEDRIVER_PATH, options=chrome_options)
  File "C:\Users\321lu\AppData\Local\Programs\Python\Python37\lib\site-packages\selenium\webdriver\chrome\webdriver.py", line 81, in __init__
  File "C:\Users\321lu\AppData\Local\Programs\Python\Python37\lib\site-packages\selenium\webdriver\remote\webdriver.py", line 157, in __init__
    self.start_session(capabilities, browser_profile)
  File "C:\Users\321lu\AppData\Local\Programs\Python\Python37\lib\site-packages\selenium\webdriver\remote\webdriver.py", line 252, in start_session
    response = self.execute(Command.NEW_SESSION, parameters)
  File "C:\Users\321lu\AppData\Local\Programs\Python\Python37\lib\site-packages\selenium\webdriver\remote\webdriver.py", line 321, in execute
    self.error_handler.check_response(response)
  File "C:\Users\321lu\AppData\Local\Programs\Python\Python37\lib\site-packages\selenium\webdriver\remote\errorhandler.py", line 242, in check_response        
    raise exception_class(message, screen, stacktrace)
selenium.common.exceptions.WebDriverException: Message: unknown error: cannot parse internal JSON template: Line: 1, column: 1, Unexpected token.
    """
    rmtree(dir)
    copy_tree(replace_dir, dir)    