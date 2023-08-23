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

# For parsing and saving
import datetime as dt
import csv
import sys
import os

from util.log_videos import get_videos, update_video_log
from util.helpers import startWebdriver, get_logging_decorator, catch_user_data_error, test_YouTube_login

from util.custom_values import DATA_DIR
from util.constants import METRICS, TimePeriod, Dimensions, ADV_URL

SCRIPT_NAME = os.path.basename(__file__)[:-len(".py")]

from util.scrape_since_publish_functions import scrape, scrape_subs, assemble_data

# OTHER -----------------------------------------------------------------------

def check_granularity(metrics_data: dict) -> dt.timedelta:
    metric_data_list = list(metrics_data.values())[0]
    category_data = metric_data_list[0]['data']
    start_dt = dt.datetime.fromtimestamp(category_data[0]['x']/1000)
    next_dt = dt.datetime.fromtimestamp(category_data[1]['x']/1000)
    time_delta = next_dt - start_dt
    return time_delta


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
        metrics_data["subs"] = scrape_subs(driver, video_id)
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
