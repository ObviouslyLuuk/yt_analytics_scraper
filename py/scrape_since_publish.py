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
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# For parsing and saving
import json
import datetime as dt
import csv
import sys

from util.log_videos import adjust_video_log, get_videos, update_video_log
from util.helpers import startWebdriver

from util.custom_values import DATA_DIR
from util.constants import METRICS, TimePeriod, TRAFFIC_SOURCES_IMP, \
    TRAFFIC_SOURCES, TRAFFIC_SOURCES_INV, DIMENSIONS, ADV_URL

# SCRAPING --------------------------------------------------------------------


def zoom_out(driver) -> bool:
    # Wait 10 seconds for the lines to show up
    lines = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'g.line-segments > path.line-series'))
    )
    # Zoom out for more accurate data
    driver.execute_script(
        'document.querySelectorAll("#yta-line-chart-base")' +
        '.forEach(e => e.style.zoom = "0.0001%")'
    )
    # Wait until the old chart goes stale
    WebDriverWait(driver, 10).until(
        EC.staleness_of(lines)
    )
    return True


def scrape(driver, totals: bool=False) -> tuple:
    """Scrapes YouTube analytics from the chart"""
    # Css selectors
    traffic_source_css = 'g.seriesGroups > g[series-id{}]'
    scale_css = 'g.y.axis > g.tick.first-tick > text > tspan'
    pane_css = 'rect.mouseCapturePane'

    if totals:
        traffic_source_css = traffic_source_css.format(
            f'="{TRAFFIC_SOURCES_INV["Total"]}"')
    else:
        traffic_source_css = traffic_source_css.format('')
    line_css = traffic_source_css + ' > g.line-segments > path.line-series'

    # Wait 10 seconds for the line element to show up
    line_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, line_css))
    )
    traffic_source = TRAFFIC_SOURCES[
        driver.find_element_by_css_selector(traffic_source_css)
        .get_attribute('series-id')
        ]
    line_string = line_element.get_attribute('d')
    height = float(driver.find_element_by_css_selector(pane_css)
                   .get_attribute('height'))
    scale_string = driver.find_element_by_css_selector(scale_css) \
        .get_attribute('innerHTML')

    return {"line": line_string, "height": height, "scale": scale_string}, \
        traffic_source

# PARSING ---------------------------------------------------------------------


def parse_scale(string: str) -> float:
    result = float(string.rstrip("KMB").replace(',', ''))
    if "K" in string:
        result *= 1e3
    elif "M" in string:
        result *= 1e6
    elif "B" in string:
        result *= 1e9

    return result


def parse_line(string: str):
    string = string.replace('M', '[[').replace('L', '],[') + ']]'
    return json.loads(string)


# TODO: Use document.querySelector('yta-line-chart-base').chartSpec
def parse_line_data(line_data: dict, time_period: TimePeriod) -> list:
    line = parse_line(line_data["line"])
    if time_period == TimePeriod.since_published:
        # Throw away last hour because it's in progress
        line.pop()
    scale_top = parse_scale(line_data["scale"])
    unit_per_y = scale_top/line_data["height"]
    time_per_x = (len(line)-1)/line[-1][0]

    scaled_line = []
    for point in line:
        scaled_line.append((
            round(point[0]*time_per_x),
            (line_data["height"] - point[1])*unit_per_y,
        ))

    return scaled_line

# OTHER -----------------------------------------------------------------------


def assemble_data(lines: dict, upload_datetime: dt.datetime, time_period: TimePeriod) -> list:
    data = []

    for metric_key, line in lines.items():
        round_dec = 0
        if "watchtime" in metric_key:
            round_dec = 2

        for time_unit, value in line:
            value = round(value, round_dec)

            time_delta = dt.timedelta(hours=time_unit)
            if time_period == TimePeriod.first_24h:
                time_delta = dt.timedelta(minutes=time_unit)

            datetime = upload_datetime + time_delta
            if len(data) <= time_unit:
                data.append({
                    "datetime(UTC)": datetime,
                    "day": datetime.strftime('%a'),
                    "time unit": time_unit,
                    "time delta": time_delta,
                    metric_key: value,
                })
            else:
                data[time_unit][metric_key] = value

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
                  "this probably means the same granularity is " +
                  "no longer available")
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


def process(video_id: str, upload_datetime: dt.datetime, dir: str='', time_period: TimePeriod=TimePeriod.since_published) -> bool:
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
    lines = {}
    base_url = ADV_URL.format(
        video_id=video_id,
        time_period=time_period.value,
        metric="{metric}",
        dimension="{dimension}"
    )
    try:
        # Get data for totals
        for metric_key, metric_code in METRICS.items():
            # Reset elements with random website
            driver.get("https://www.pictureofhotdog.com/")

            url = base_url.format(metric=metric_code, dimension=DIMENSIONS[0])
            driver.get(url)

            zoom_out(driver)

            line_datum, _ = scrape(driver, totals=True)
            lines[metric_key] = parse_line_data(line_datum, time_period)

        # Get data per traffic source
        for metric_key, metric_code in METRICS.items():
            # likes and dislikes aren't measured per traffic source, so skip
            if metric_key in ["likes", "dislikes"]:
                continue

            line_data = {}

            # Reset elements with random website
            driver.get("https://www.pictureofhotdog.com/")

            url = base_url.format(metric=metric_code, dimension=DIMENSIONS[1])
            driver.get(url)

            zoom_out(driver)

            # Wait 10 seconds for the checkbox elements to show up
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '.breakdown-row #checkbox-container'))
            )
            checkboxes = driver.find_elements_by_css_selector(
                '.breakdown-row #checkbox-container')
            for checkbox in checkboxes:
                checkbox.click()
                line_datum, traffic_source = scrape(driver)

                # Don't save stuff that's not logged for impressions
                if metric_key != "impressions" or \
                   traffic_source in TRAFFIC_SOURCES_IMP.values():
                    line_data[f"{metric_key}_{traffic_source}"] = line_datum

                checkbox.click()

            for key, line_datum in line_data.items():
                line_data[key] = parse_line_data(line_datum, time_period)

            lines.update(line_data)

            # Add empty traffic sources for the fieldnames
            traffic_sources = TRAFFIC_SOURCES.values()
            if metric_key == "impressions":
                traffic_sources = TRAFFIC_SOURCES_IMP.values()

            for traffic_source in traffic_sources:
                if f"{metric_key}_{traffic_source}" not in lines and \
                   traffic_source != "Total":
                    lines[f"{metric_key}_{traffic_source}"] = [[0, 0]]
    finally:
        driver.quit()

    video_data = assemble_data(lines, upload_datetime, time_period)
    if not save_data(video_data, f"{time_period.name}_{video_id}", dir):
        return False
    return True


# MAIN ------------------------------------------------------------------------

if __name__ == "__main__":
    # Get command line argument
    try:
        time_period = TimePeriod[sys.argv[1]]
    except IndexError:
        time_period = TimePeriod.since_published
        print(f"No time period given: defaulting to {time_period.name}")
    except KeyError:
        print("Usage: python scrape_since_publish.py <first_24h / since_published>")

    # Scrape data for videos where hourly data is still displayed
    update_video_log()
    recent_videos = get_videos()

    for video in recent_videos:
        still_recent = process(video["id"], video["date"], DATA_DIR, time_period)
        if not still_recent:
            adjust_video_log(
                video["date"],
                video["id"],
                video["title"],
                recent=0,
            )
