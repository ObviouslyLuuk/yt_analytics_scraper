# For parsing and saving
import datetime as dt
import os

from util.helpers import wait_for_element

from util.constants import METRICS, TimePeriod, TRAFFIC_SOURCES_IMP, \
    TRAFFIC_SOURCES, Dimensions, ADV_URL

SCRIPT_NAME = os.path.basename(__file__)[:-len(".py")]


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



def scrape_video_basics_by_analytics(driver, video_id) -> tuple:
    """Scrape the datetime of the video from the YouTube analytics page. Return as a tuple of title str and datetime object."""
    metric = "impressions"
    url = ADV_URL.format(
        video_id=video_id,
        time_period=TimePeriod.since_published.value,
        metric=METRICS[metric],
        dimension=Dimensions.traffic_source.value
    )
    metrics_data = {}
    driver.get(url)
    metrics_data[metric] = scrape(driver)
    title = driver.execute_script("return document.getElementById('search-box-text').innerHTML")
    return (title, assemble_data(metrics_data)[0]["datetime(UTC)"])



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
