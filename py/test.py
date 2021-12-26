# Selenium stuff
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from util.custom_values import CHROMEDRIVER_PATH, CHROME_PROFILES, CHROME_PROFILE, DATA_DIR
from util.helpers import reset_user_data

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

if __name__ == "__main__":
    import os
    reset_user_data(os.path.join(DATA_DIR, "User Data"), os.path.join(DATA_DIR, "backup/User Data(backup)"))
    driver = startWebdriver()
    driver.quit()

