###############################################################################
#
# time_period=since_published:
# Script to scrape hourly YouTube analytics for the time
# since the upload of a video.
# This should be possible for videos younger than 30 days
#
# time_period=24h:
# Script to scrape YouTube analytics from the first 24 hours of a video.
# This should be possible for any videos uploaded past a certain date,
# so no specific age.
#
# started on 17-08-2021
# made by Luuk
#
###############################################################################

# Selenium stuff
# For a custom wait
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# For parsing and saving
import datetime as dt
import csv
import sys
import os

from util.log_videos import adjust_video_log, get_videos, update_video_log
from util.helpers import startWebdriver, get_logging_decorator, catch_user_data_error, test_YouTube_login, wait_for_element

from util.custom_values import DATA_DIR
from util.constants import METRICS, TimePeriod, TRAFFIC_SOURCES_IMP, \
    TRAFFIC_SOURCES, Dimensions, ADV_URL

SCRIPT_NAME = os.path.basename(__file__)[:-len(".py")]

# SCRAPING --------------------------------------------------------------------

def scrape(driver) -> list:
    """
    Scrape YouTube analytics from the chart. Return list of the different 
    dimension categories with data for the loaded webpage.
    like:
        [
            {
                "data": [
                    {
                        "hovercardInfo": {
                            "relativeDateFormatted": <relative time since upload, eg 'First 2 days'>,
                            "entityTitle": <plaintext category name, eg End Screens>,
                        },
                        "x": <int: millisecond timestamp of datapoint>,
                        "y": <int: metric value>,
                    },
                ],
                "name": <category name, eg 'END_SCREEN_main'>,
            },
        ]
    """
    # Css selectors
    chart_css = 'yta-line-chart-base'

    # Wait max 10 seconds for the line element to show up
    wait_for_element(driver, chart_css)
    metric_data_list = []
    totals_data = driver.execute_script("return document.querySelector('#explore-app > yta-explore-deep-dive').fetchedData.data.chartProperties.mainMetricData.data[0].totalsSeries")
    series_data_array = driver.execute_script("return Array.from( document.querySelector('#explore-app > yta-explore-deep-dive').fetchedData.data.chartProperties.mainMetricData.data[0].series.values() )")
    metric_data_list.append(totals_data)
    metric_data_list.extend(series_data_array)

    return metric_data_list

# OTHER -----------------------------------------------------------------------

def check_granularity(metrics_data: dict) -> dt.timedelta:
    metric_data_list = list(metrics_data.values())[0]
    category_data = metric_data_list[0]['data']
    start_dt = dt.datetime.fromtimestamp(category_data[0]['x']/1000)
    next_dt = dt.datetime.fromtimestamp(category_data[1]['x']/1000)
    time_delta = next_dt - start_dt
    return time_delta


def assemble_data(metrics_data: dict) -> list:
    data = []

    for metric_key, metric_data_list in metrics_data.items():
        value_fn = lambda x: x
        if metric_key == "watchtime":
            metric_key += "(Hours)"
            factor = 1/60/60/1000 # Originally the watchtime data is in milliseconds
            value_fn = lambda x: round(x*factor, 2)

        for category in metric_data_list:
            try:
                traffic_source = TRAFFIC_SOURCES[category['name']]
            except KeyError:
                print("Unknown traffic source: YouTube has likely added some")
                return None

            # Don't save stuff that's not logged for impressions
            if metric_key == "impressions" and \
                traffic_source not in TRAFFIC_SOURCES_IMP.values():
                continue            

            for time_unit, datapoint in enumerate(category['data']):
                datetime = dt.datetime.fromtimestamp(datapoint['x']/1000, dt.timezone.utc)
                value = value_fn(datapoint['y'])
                time_delta = datapoint['hovercardInfo']['relativeDateFormatted'] # Time delta from publish time

                if len(data) <= time_unit:
                    # Add new row when necessary
                    data.append({
                        "datetime(UTC)": datetime,
                        "day": datetime.strftime('%a'),
                        "time unit": time_unit,
                        "time delta": time_delta,
                        f"{metric_key}_{traffic_source}": value,
                    })
                else:
                    # Add value to row
                    data[time_unit][f"{metric_key}_{traffic_source}"] = value

        # Add empty traffic sources for the fieldnames:
        # Sometimes a traffic source isn't listed because there is no
        # data on it yet, but in the future there might be so we want to
        # include it for the fieldnames in the csv
        traffic_sources = TRAFFIC_SOURCES.values()
        if metric_key == "impressions":
            traffic_sources = TRAFFIC_SOURCES_IMP.values()
        elif metric_key in ["likes", "dislikes"]:
            traffic_sources = ["Total"]

        for traffic_source in traffic_sources:
            if f"{metric_key}_{traffic_source}" in data[0]:
                continue
            data[0][f"{metric_key}_{traffic_source}"] = 0

    return data


def save_data(data: list, title: str="data", dir: str='') -> bool:
    filepath = dir + f"{title}.csv"

    try:
        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            read_data = []
            for row in reader:
                read_data.append(row)

        if len(data) < len(read_data):
            print("less data scraped than is already logged.\n" +
                  "this is weird because granularity should " +
                  "already be checked.")
            return False
    except FileNotFoundError:
        print(f"Making new file: {title}")

    # Since this data is available all at once there's no need to append,
    # can just overwrite
    with open(filepath, "w", newline='') as f:
        writer = csv.DictWriter(f, data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        print(f"Written scraped data to {title}")
    return True


def process(video_id: str, dir: str='', 
time_period: TimePeriod=TimePeriod.since_published) -> bool:
    """
    Scrape video analytics from YouTube. Save to csv.

    Parameters
    ----------
    video_id : str
        The id of the video.
    upload_datetime : dt.datetime
        The datetime when the video was published.
    dir : str, optional
        Directory where the data csv files should go.
    time_period : TimePeriod, optional
        Either TimePeriod.since_published or TimePeriod.first_24h.

    Returns
    -------
    bool
        True if data was saved, False if not.
    """
    # Scrape data
    driver = startWebdriver()
    metrics_data = {}
    base_url = ADV_URL.format(
        video_id=video_id,
        time_period=time_period.value,
        metric="{metric}",
        dimension="{dimension}"
    )
    try:
        # Get data for totals and per traffic source
        for metric_key, metric_code in METRICS.items():
            # Reset elements with random website
            driver.get("https://www.pictureofhotdog.com/")

            url = base_url.format(metric=metric_code, dimension=Dimensions.traffic_source.value)
            driver.get(url)

            metrics_data[metric_key] = scrape(driver)
    finally:
        driver.quit()

    # We want at least hourly data
    time_delta = check_granularity(metrics_data)
    if time_delta > dt.timedelta(hours=2):
        print("timedelta between datapoints is larger than 2 hours")
        return False
    
    # We don't want minutes if we're getting since_published, which should be hourly
    if time_delta < dt.timedelta(minutes=2):
        print("timedelta between two datapoints is smaller than 2 minutes")
        return False

    video_data = assemble_data(metrics_data)
    if not save_data(video_data, f"{time_period.name}_{video_id}", dir):
        return False
    return True


# MAIN ------------------------------------------------------------------------

@get_logging_decorator(os.path.join(DATA_DIR, "script_logs", SCRIPT_NAME))
@catch_user_data_error
def main():
    # Get command line argument
    try:
        time_period = TimePeriod[sys.argv[1]]
    except IndexError:
        time_period = TimePeriod.since_published
        print(f"No time period given: defaulting to {time_period.name}")
    except KeyError:
        print("Usage: python scrape_since_publish.py <first_24h / since_published>")

    # Test webdriver and login, and log details
    driver = startWebdriver(printing=True)
    try:
        test_YouTube_login(driver)
    finally:
        driver.quit()

    # Scrape data for videos 
    # Only where hourly data is still displayed if time_period is since published
    update_video_log()
    recent_videos = get_videos(time_period == TimePeriod.since_published)

    if len(recent_videos) < 1:
        print("Scrape since publish: no recent videos found")

    for video in recent_videos:
        process(video["id"], DATA_DIR, time_period)

if __name__ == "__main__":
    main()
