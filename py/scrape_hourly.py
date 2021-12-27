###############################################################################
#
# Script to scrape YouTube realtime views data
#
# started on 17-08-2021
# made by Luuk
#
###############################################################################

# Selenium stuff
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# For parsing and saving
import json
import datetime as dt
import csv
import os

from util.log_videos import get_videos, update_video_log
from util.helpers import startWebdriver, get_logging_decorator, catch_user_data_error

from util.custom_values import CHANNEL_ID, DATA_DIR
from util.constants import ScrapeMode, ANALYTICS_URL, DAYS_OF_THE_WEEK

SCRIPT_NAME = os.path.basename(__file__)[:-len(".py")]

# SCRAPING --------------------------------------------------------------------


def scrape(driver, URL: str) -> str:
    """Scrapes YouTube analytics for the recent data from the mini-card"""
    # Open URL
    driver.get(URL)

    # Wait a second so you're not locating the page that was already loaded
    time.sleep(1)

    # Wait 10 seconds for the information element to show up
    card_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//yta-latest-activity-card"))
    )
    return card_element.get_attribute("mini-card")

# PARSING ---------------------------------------------------------------------


def parse_hour(date_str: str) -> tuple:
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


def parse_datetime(row: dict) -> dt.datetime:
    return dt.datetime.strptime(f'{row["date"]} {row["start"]}', '%Y-%m-%d %H:%M')


def parse_string(string: str) -> dict:
    # Get en hyphen character and replace with normal hyphen
    char = json.loads(string) \
        ["last48HoursData"]["mainChart"]["data"][0]["hovercardInfo"]["domainText"] \
        .split(',')[1].lstrip(' :APM0123456789').split(' ')[0]
    return json.loads(string.replace(char, '-'))

# OTHER -----------------------------------------------------------------------


def init_date(last_updated: str) -> dict:
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


def assemble_data(card_obj: dict, date_dict: dict, mode: ScrapeMode) -> list:
    data = []

    for datapoint in card_obj['last48HoursData']['mainChart']['data']:
        start_time, end_time = parse_hour(
            datapoint['hovercardInfo']['domainText'])
        date = date_dict[
            datapoint['hovercardInfo']['domainText'].split(',')[0]
        ]

        data.append({
            "date": date,
            "start": start_time,
            "end": end_time,
            "day": date.strftime('%a'),
            "views": datapoint['y'],
        })

    if mode == ScrapeMode.channel:
        for category in card_obj['last48HoursData']['table']:
            try:
                video_id = category \
                    ['analyticsLink']['routeLink']['route']['params']['videoId']
            except KeyError:
                video_id = category['thumbnailData']['thumbnailUrl'].split('/')[4]

            value = int(category['value'].replace(',', ''))
            percentage_data = category['sparkChartPercentages']
            percent_sum = sum(percentage_data)
            views_per_percent = value / percent_sum

            for i, datapoint in enumerate(data):
                datapoint[video_id] = int(percentage_data[i] * views_per_percent)
                data[i] = datapoint
    elif mode == ScrapeMode.video:
        total_value = int(card_obj['last48HoursData']['totalMetricValue']
                          .replace(',', ''))
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

    # pop last datapoint because it is ongoing
    data.pop()

    return data


def save_data(data: list, title: str, dir: str='') -> None:
    filepath = dir + f"{title}.csv"

    try:
        # Read existing data to see what the last datapoint is
        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            read_data = []
            for row in reader:
                read_data.append(row)
    except FileNotFoundError:
        read_data = False
        print(f"Making new file: {title}")

    if read_data:
        for key in data[-1].keys():
            if key not in fieldnames:
                fieldnames.append(key)

        # If there's no overlap
        if parse_datetime(data[0]) > parse_datetime(read_data[-1]):
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

        else:
            # Append only new data
            # Check at what index the new data starts
            index = 0
            for row in data:
                if parse_datetime(row) > parse_datetime(read_data[-1]):
                    break
                index += 1
            data = data[index:]

        if len(data) < 1:
            print("No new realtime data to add")
            return
        # # Can't append because sometimes new columns are added
        # # which requires an update to the header
        # with open(filepath, "a", newline='') as f:
        #     writer = csv.DictWriter(f, fieldnames)
        #     writer.writerows(data)

        read_data.extend(data)
        data = read_data

    else:
        # Write new file if there was none
        fieldnames = data[-1].keys()

    with open(filepath, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames)
        writer.writeheader()
        writer.writerows(data)
        print(f"Written scraped data to {title}")


def process(mode: ScrapeMode=ScrapeMode.channel, video_id: str='', 
dir: str='') -> None:
    """Weaves all basic functionality together"""
    # Scrape data
    driver = startWebdriver()
    try:
        id = CHANNEL_ID
        if mode == ScrapeMode.video:
            id = video_id
        card = scrape(driver, ANALYTICS_URL.format(mode=mode.name, id=id))
    finally:
        driver.quit()

    card_obj = parse_string(card)

    date_dict = init_date(card_obj["lastUpdated"])

    data = assemble_data(card_obj, date_dict, mode)
    save_data(data, f"Hourly_{id}", dir)

# MAIN ------------------------------------------------------------------------

@get_logging_decorator(os.path.join(DATA_DIR, "script_logs", SCRIPT_NAME))
@catch_user_data_error
def main():
    process(dir=DATA_DIR)

    # Get data for the two most recent videos
    # They don't need to be younger than a month
    update_video_log()
    for video in get_videos(False)[-2:]:
        process(ScrapeMode.video, video["id"], DATA_DIR)

if __name__ == "__main__":
    main()
