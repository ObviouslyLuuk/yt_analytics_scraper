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
from util.helpers import startWebdriver, catch_user_data_error, test_YouTube_login, wait_for_element
from util.log_errors import get_logging_decorator

from util.custom_values import CHANNEL_ID, DATA_DIR
from util.constants import ScrapeMode, ANALYTICS_URL, DAYS_OF_THE_WEEK

SCRIPT_NAME = os.path.basename(__file__)[:-len(".py")]

# SCRAPING --------------------------------------------------------------------


def scrape(driver, URL: str) -> str:
    """
    Scrapes YouTube analytics for the recent data from the card.
    like:
        {
            "last48HoursData": {
                "totalMetricValue": <str: total views in the timeframe, eg '745'>,
                "mainChart": {
                    "data": [
                        {
                            "hovercardInfo": {
                                "domainText": <Timeframe, eg 'Monday, 1:00 - 2:00 PM'>
                            },
                            "x": <int: millisecond timestamp of datapoint>,
                            "y": <int: metric value>,
                        },
                    ],
                },
                "table": [
                    {
                        "sparkChartPercentages": [
                            <float: percentage of chart height>
                        ],
                        "title": <name of traffic source, eg 'Channel pages'>,
                        "value": <str: percentage this traffic source is of the total, eg '70.6%'>,
                    }
                ],
            },
            "last60MinutesData": {
                <same as last48HoursData>
            }
        }
    """
    # Open URL
    driver.get(URL)

    card_css = "yta-latest-activity-card"

    # Wait 10 seconds for the information element to show up
    wait_for_element(driver, card_css)
    card_data = driver.execute_script(f"return document.querySelector('{card_css}').card")
    return card_data

# OTHER -----------------------------------------------------------------------

def assemble_data(card_obj: dict, mode: ScrapeMode) -> list:
    data = []

    for datapoint in card_obj['last48HoursData']['mainChart']['data']:
        datetime = dt.datetime.fromtimestamp(datapoint['x']/1000, dt.timezone.utc)

        data.append({
            "datetime(UTC)": datetime,
            "day": datetime.strftime('%a'),
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

    # ignore last datapoint because it is ongoing
    return data[:-1]


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

        # Append only new data
        # Check at what index the new data starts
        index = 0
        for row in data:
            if row['datetime(UTC)'] > dt.datetime.strptime(read_data[-1]['datetime(UTC)'], "%Y-%m-%d %H:%M:%S%z"):
                break
            index += 1
        data = data[index:]

        if len(data) < 1:
            print("No new realtime data to add")
            return

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
        card_data = scrape(driver, ANALYTICS_URL.format(mode=mode.name, id=id))
    finally:
        driver.quit()

    data = assemble_data(card_data, mode)
    save_data(data, f"Hourly_{id}", dir)
    return data[-1].keys()

# MAIN ------------------------------------------------------------------------

@get_logging_decorator(os.path.join(DATA_DIR, "script_logs", SCRIPT_NAME))
@catch_user_data_error
def main():
    # Test webdriver and login, and log details
    driver = startWebdriver(printing=True)
    try:
        test_YouTube_login(driver, email=True)
    finally:
        driver.quit()

    # Get hourly channel data
    keys = process(dir=DATA_DIR)
    relevant_video_ids = [k for k in keys if k not in ['datetime(UTC)', 'day', 'views']] # this is always three ids

    # Get data for recent videos
    update_video_log()

    # If the video is younger than 30 days, skip
    # Because this data can still be scraped from since_published, and that's more precise
    videos = get_videos(False)
    last_n = 2
    too_young_ids = [vid['id'] for vid in videos if dt.datetime.utcnow() - vid['date'] < dt.timedelta(days=30)]
    last_video_ids = [vid['id'] for vid in videos[-last_n:] if vid['id'] not in too_young_ids] # last n videos
    if len(last_video_ids) < 1:
        print(f"Last {last_n} videos are <30 days old; should still be scraped with since_published (more precise)")

    scrape_video_ids = list(set(relevant_video_ids).union(set(last_video_ids)).difference(set(too_young_ids)))
    if len(scrape_video_ids) < 1:
        print("Relevant 3 videos are all <30 days old; should be scraped with since_published (more precise)")
    for video_id in scrape_video_ids:
        process(ScrapeMode.video, video_id, DATA_DIR)

if __name__ == "__main__":
    main()
