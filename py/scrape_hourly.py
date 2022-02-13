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

    # Wait a second so you're not locating the page that was already loaded
    time.sleep(1)

    card_css = "yta-latest-activity-card"

    # Wait 10 seconds for the information element to show up
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, card_css))
    )
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

        # If there's no overlap
        if data[0]['datetime(UTC)'] > dt.datetime.strptime(read_data[-1]['datetime(UTC)'], "%Y-%m-%d %H:%M:%S%z"):
            # Add missing in-between hours
            new_data = []
            new_datetime = dt.datetime.strptime(read_data[-1], "%Y-%m-%d %H:%M:%S%z") + dt.timedelta(hours=1)
            # TODO: stop this madness and find a better, more storage efficient way
            while new_datetime < data[0]['datetime(UTC)']:
                new_data.append({
                    "datetime(UTC)": new_datetime,
                    "day": new_datetime.strftime('%a'),
                    "views": "X",
                })
                new_datetime += dt.timedelta(hours=1)
            new_data.extend(data)
            data = new_data

        else:
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
