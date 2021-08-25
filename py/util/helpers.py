# Selenium stuff
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from .custom_values import CHROMEDRIVER_PATH, CHROME_PROFILES, CHROME_PROFILE


def startWebdriver() -> webdriver.Chrome:
    """Starts the selenium webdriver and adds options"""
    chrome_options = Options()
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-data-dir="+CHROME_PROFILES)
    chrome_options.add_argument("profile-directory="+CHROME_PROFILE)
    # chrome_options.add_argument("--window-size=10,10")
    chrome_options.add_argument("--start-maximized")

    return webdriver.Chrome(CHROMEDRIVER_PATH, options=chrome_options)