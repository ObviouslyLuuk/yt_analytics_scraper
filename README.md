# yt_analytics_scraper
This tool uses selenium and a chrome webdriver to scrape YouTube for analytics data (because YouTube doesn't store it forever). It then saves/appends the data to a csv file.

# Usage:
Change the values at the top of scrape.py for your custom use.
- Prior to this you'll need to download a Google Chrome webdriver that corresponds to your version of Google Chrome. You can do that [here](https://chromedriver.chromium.org/downloads).
    - Check which version of Chrome you have in the settings of your browser
- You'll also need a Google Chrome profile that's already logged into the desired YouTube account, as to avoid having to enter your login information (which Google forbids bots to do anyway if you've got 2-factor authentication enabled). You'll find this profile at C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data\\ <br>
If you want to be safe: 
    - create a new profile
    - login to your YouTube channel on it 
    - copy the "User Data" folder (which includes your new profile) to a separate location (you need to close Chrome for this step)
    - fill that path and profile folder name into the custom_values.py file
## Windows:
Make sure the exec_scrape.bat file contains the correct path for your location of scrape.py.
### Open Windows Task Scheduler [(helpful tutorial for this)](https://towardsdatascience.com/automate-your-python-scripts-with-task-scheduler-661d0a40b279)
<i>(Options or checkboxes not mentioned shouldn't be enabled)</i>
> Create Basic Task...
- Give Name and Description
- <button>Next</button>
> Trigger
- Daily
- <button>Next</button>
    - Start: \[some time in the future\]
    - Recur every: \[1\] days
    - <button>Next</button>
> Action
- Start a program
- <button>Next</button>
    - Program/script: \[browse for the batch file\]
    - <button>Next</button>
> Finish
- <input type="checkbox" checked=true> Open the Properties dialog ...
- <button>Finish</button>

#### (Properties dialog)
> General
- <input type="checkbox" checked=true> Run whether use is logged on or not
- <input type="checkbox" checked=true> Do not store password...
- <input type="checkbox" checked=true> Run with highest privileges
- <input type="checkbox" checked=true> Hidden
- Configure for: \[your windows version, but doesn't seem to matter\]
> Conditions
- <input type="checkbox" checked=true> Wake the computer to run this task
> Settings
- <input type="checkbox" checked=true> Allow task to be run on demand
- <input type="checkbox" checked=true> Run task as soon as possible...
- If the task fails, restart every: \[1 minute\]
- Attempt to restart up to: \[3 times\]
- Stop the task if it runs longer than: \[1 hour\]
- <input type="checkbox" checked=true> If the running task does not end... force it to stop

<br></br>
### Control Panel
- Hardware and Sound
- Power Options
- Change plan settings
- Change advanced power settings
    - Sleep
        - Allow wake timers
            - \[Enable / Important Wake Timers Only\]