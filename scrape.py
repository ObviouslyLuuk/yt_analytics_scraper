###############################################################################
#
# Script to scrape YouTube realtime views data
# 
# started on 17-08-2021
# made by Luuk
#
###############################################################################

# Selenium stuff
from selenium import webdriver
# For headless etc
from selenium.webdriver.chrome.options import Options
# # For sending keys like ENTER
# from selenium.webdriver.common.keys import Keys
# # For moving the cursor (for example)
# from selenium.webdriver.common.action_chains import ActionChains
# # For a custom wait
# from selenium.common.exceptions import NoSuchElementException, TimeoutException
# For waiting
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# For parsing and saving
import json
import datetime as dt
import csv
import os

# CONSTANTS -------------------------------------------------------------------

CHANNEL_ID          = "UChXogayC52mlROq-N71_f5g"
DATA_DIR            = "D:\\Users\\Luuk\\Documents\\Programming\\stuff\\yt_realtime_data\\"
CHROMEDRIVER_PATH   = "C:\\chromedriver\\chromedriver"
# Copy this from       C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data\\
CHROME_PROFILES     = "D:\\Users\\Luuk\\Documents\\Programming\\stuff\\yt_realtime_data\\User Data\\"
# Use a profile that's already logged in to YouTube
CHROME_PROFILE      = "Profile 4"

THUMBNAIL_URL       = "http://img.youtube.com/vi/{}/maxresdefault.jpg"
DAYS_OF_THE_WEEK    = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# SCRAPING --------------------------------------------------------------------

def startWebdriver():
    """Starts the selenium webdriver and adds options"""
    chrome_options = Options()
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-data-dir="+CHROME_PROFILES)
    chrome_options.add_argument("profile-directory="+CHROME_PROFILE)
    chrome_options.add_argument("--window-size=10,10")

    # chrome_options.add_argument("user-data-dir=C:\\Users\\321lu\\AppData\\Local\\Google\\Chrome\\User Data\\")
    # chrome_options.add_argument("profile-directory=Profile 4")
    # chrome_options.add_argument("start-maximized")
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument( # Add user-agent to fool chrome into thinking it isn't headless (not working)
    #     # https://stackoverflow.com/questions/66612934/some-websites-dont-fully-load-render-in-selenium-headless-mode
    #     "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
    # )

    return webdriver.Chrome(CHROMEDRIVER_PATH, options=chrome_options)


def scrape(driver, URL):
    """Scrapes YouTube analytics for the recent data from the mini-card"""
    # Open URL
    driver.get(URL)
    time.sleep(1) # Wait a second to make sure you're not locating the page that was already loaded

    # Wait 10 seconds for the information element to show up
    card_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//yta-latest-activity-card"))
    )
    return card_element.get_attribute("mini-card")

# PARSING ---------------------------------------------------------------------

def parse_hour(date_str):
    # Remove days from date_str
    days = DAYS_OF_THE_WEEK.copy()
    days.extend(["Today", "Yesterday", "Tomorrow"])
    for day in days:
        date_str = date_str.replace(day+", ", "")

    # Split into start and end, and add AM/PM to start where necessary
    hour_split = date_str.split('-')
    start = hour_split[0]
    end = hour_split[1].lstrip(' ')
    if len(start.rstrip(' ').split(' ')) == 1:
        start += end.split(' ')[1]
    else:
        start = start.rstrip(' ')

    # Turn into 24-hour scale
    start_time = dt.datetime.strptime(start, '%I:%M %p').strftime('%H:%M')
    end_time = dt.datetime.strptime(end, '%I:%M %p').strftime('%H:%M')

    return start_time, end_time


def parse_datetime(row):
    return dt.datetime.strptime(f'{row["date"]} {row["start"]}', '%Y-%m-%d %H:%M')


def parse_string(string):
    # Get en hyphen character and replace with normal hyphen
    char = json.loads(string)["last48HoursData"]["mainChart"]["data"][0]["hovercardInfo"]["domainText"].split(',')[1].lstrip(' :APM0123456789').split(' ')[0]
    return json.loads(string.replace(char,'-'))

# OTHER -----------------------------------------------------------------------

def init_date(last_updated):
    # Call the last updated date "Today"
    datetime_str = last_updated.split(".")[0]
    datetime = dt.datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S')
    today = datetime.date()

    # today = dt.date.today()
    yesterday = today - dt.timedelta(days=1)
    day_before_yesterday = today - dt.timedelta(days=2)

    # Make dictionary to replace day names with actual dates
    date_dict = {
        "Today": today,
        "Yesterday": yesterday,
    }
    for day in DAYS_OF_THE_WEEK:
        date_dict[day] = day_before_yesterday

    return date_dict


def assemble_data(card_obj, date_dict, mode="channel"):
    data = []

    for datapoint in card_obj['last48HoursData']['mainChart']['data']:
        start_time, end_time = parse_hour(datapoint['hovercardInfo']['domainText'])
        date = date_dict[datapoint['hovercardInfo']['domainText'].split(',')[0]]

        data.append({
            "date": date,
            "start": start_time,
            "end": end_time,
            "day": date.strftime('%a'),
            "views": datapoint['y'],
        })

    if mode == "channel":
        for category in card_obj['last48HoursData']['table']:
            video_id = category['thumbnailData']['thumbnailUrl'].split('/')[4]
            thumb_url = THUMBNAIL_URL.format(video_id)
            value = int(category['value'].replace(',', ''))
            percentage_data = category['sparkChartPercentages']
            percent_sum = sum(percentage_data)
            views_per_percent = value / percent_sum

            for i, datapoint in enumerate(data):
                datapoint[thumb_url] = int(percentage_data[i] * views_per_percent)
                data[i] = datapoint
    elif mode == "video":
        total_value = int(card_obj['last48HoursData']['totalMetricValue'].replace(',', ''))
        for category in card_obj['last48HoursData']['table']:
            title = category['title']
            percentage = float(category['value'].rstrip('%'))/100
            value = percentage*total_value
            percentage_data = category['sparkChartPercentages']
            percent_sum = sum(percentage_data)
            views_per_percent = value / percent_sum

            for i, datapoint in enumerate(data):
                datapoint[title] = int(percentage_data[i] * views_per_percent)
                data[i] = datapoint

    data.pop() # pop last datapoint because it is ongoing

    return data


def save_data(data, title="data", dir=''):
    filepath = dir + f"{title}.csv"

    try: # Read existing data to see what the last datapoint is
        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            read_data = []
            for row in reader:
                read_data.append(row)
    except FileNotFoundError:
        read_data = False

    if read_data:
        if parse_datetime(data[0]) > parse_datetime(read_data[-1]): # If there's no overlap
            # Add missing in-between hours
            new_data = []
            new_datetime = parse_datetime(read_data[-1]) + dt.timedelta(hours=1)
            while new_datetime < parse_datetime(data[0]):
                new_data.append({
                    "date": new_datetime.strftime('%Y-%m-%d'),
                    "start": new_datetime.strftime('%H:%M'),
                    "end": (new_datetime + dt.timedelta(hours=1)).strftime('%H:%M'),
                    "day": new_datetime.strftime('%a'),
                    "views": "missing",
                })
                new_datetime += dt.timedelta(hours=1)
            new_data.extend(data)
            data = new_data
        else: # Append only new data
            # Check at what index the new data starts
            index = 0
            for row in data:
                if parse_datetime(row) > parse_datetime(read_data[-1]):
                    break
                index += 1
            data = data[index:]

        if len(data) > 0:
            with open(filepath, "a", newline='') as f:
                writer = csv.DictWriter(f, data[-1].keys())
                writer.writerows(data)

    else: # Write new file if there was none
        with open(filepath, "w", newline='') as f:
            writer = csv.DictWriter(f, data[-1].keys())
            writer.writeheader()
            writer.writerows(data)


def process(string=None, mode="channel", dir=''):
    """Weaves all basic functionality together"""
    if not string: # Scrape data
        driver = startWebdriver()
        try:
            channel_card = scrape(driver, f"https://studio.youtube.com/channel/{CHANNEL_ID}/analytics/tab-overview/period-default")

            # Get video_id of the most recent video from link on page
            link = driver.find_element_by_xpath("//a[@class='remove-default-style style-scope yta-video-snapshot-carousel']").get_attribute('href')
            video_id = link.split('/')[-4]

            video_card = scrape(driver, f"https://studio.youtube.com/video/{video_id}/analytics/tab-overview/period-default")
        finally:
            driver.quit()

        card_obj = {
            "channel": parse_string(channel_card),
            "video": parse_string(video_card),
        }
    else: # Process string
        card_obj = {"channel": False, "video": False}
        card_obj[mode] = parse_string(string)
        if mode == "video":
            video_id = card_obj[mode]["exploreConfig"]["restrictAndTimePeriodConfig"]["entity"]["id"]

    date_dict = init_date(card_obj[mode]["lastUpdated"])
    
    if card_obj["channel"]:
        channel_data = assemble_data(card_obj["channel"], date_dict, "channel")
        save_data(channel_data, "channel_mainChart", dir)
    if card_obj["video"]:
        video_data = assemble_data(card_obj["video"], date_dict, "video")
        save_data(video_data, f"{video_id}_mainChart", dir)


# MAIN ------------------------------------------------------------------------

if __name__ == "__main__":
    process(dir=DATA_DIR)

    # # Parse strings and save
    # dir = DATA_DIR+"data\\"
    # filenames = os.listdir(dir)
    # name = "EnergyStuck"
    # for filename in filenames:
    #     if name not in filename:
    #         continue

    #     with open(dir+filename, "r") as f:
    #         string = f.read()
    #     process(string, "video", DATA_DIR)