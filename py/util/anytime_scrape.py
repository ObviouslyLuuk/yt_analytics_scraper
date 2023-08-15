"""
Data that should be able to be scraped into perpetuity, without disappearing. So we don't need to do this on a schedule.
We're not talking about basic stuff like video ids, titles etc, that's in other files, because it's required.

Technically 24h from since_published.py falls into this (it remains minute data), but because it's only a parameter change from since_published it's there.
Since_published is hourly for the first month but then becomes daily, so it's not included here.

Heatmap/audience retention falls into this. It only becomes available a certain time after the video is published, but it's not going to disappear.
"""

import json

from util.constants import VIDEO_URL
from util.helpers import wait_for_element

def scrape_heatmap_data(driver, video_id):
    """
    Video heatmap data through selenium and the video page. 
    This is not available until a certain time after the video is published, but it's not going to disappear.
    Returns list of dicts, each dict is a point in the heatmap.
    time: point["heatMarkerRenderer"]["timeRangeStartMillis"]
    score: point["heatMarkerRenderer"]["heatMarkerIntensityScoreNormalized"]
    """
    url = VIDEO_URL.format(video_id=video_id)
    driver.get(url)
    wait_for_element(driver, 'div.ytp-heat-map-container')
    # wait_for_element(driver, 'path.ytp-heat-map-path') # This is the actual heatmap, but it's not always present
    html = driver.page_source

    find_str = '"heatMarkers":'
    if html.find(find_str) == -1:
        raise Exception('Heatmap data not found')

    json_str = html[html.find('"heatMarkers":') + len(find_str):]
    # json_str = json_str[:json_str.find(']') + 1]
    counter_curly = 0
    counter_square = 0
    for i, c in enumerate(json_str):
        if c == '{':
            counter_curly += 1
        elif c == '}':
            counter_curly -= 1
        elif c == '[':
            counter_square += 1
        elif c == ']':
            counter_square -= 1
        if counter_curly == 0 and counter_square == 0:
            break
    heatmap_data = json.loads(json_str[:i + 1])

    return heatmap_data