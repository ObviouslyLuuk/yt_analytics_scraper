"""
This seems to have stopped working because it says the quota is exceeded.
I don't think there used to be a quota, because you could just test without being logged in. However, the day after, it works again?
Test at: https://developers.google.com/youtube/v3/docs/videos/list?apix=true
"""

# Selenium stuff
# For a custom wait
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import json
import datetime as dt
from typing import List, Dict, Union

from .api_scrape_utils import parse_channel_item, parse_playlist_item, parse_video_item_str, scrape_api_response, clean_response

API_URL             = "https://developers.google.com/youtube/v3/docs/{mode}/list?apix=true"
API_CHANNELS_PARTS  = "snippet,contentDetails,statistics"
API_PLAYLIST_PARTS  = "contentDetails"
# url = "https://developers.google.com/youtube/v3/docs/channels/list?apix=true&apix_params=%7B%22part%22%3A%5B%22snippet%2CcontentDetails%2Cstatistics%22%5D%2C%22maxResults%22%3A50%7D"
# API_PLAYLIST_PARTS = "contentDetails,id,snippet"
# API_PLAYLIST_URL = "https://developers.google.com/youtube/v3/docs/playlistItems/list?apix=true&apix_params=%7B%22part%22%3A%5B%22contentDetails%2Csnippet%22%5D%2C%22maxResults%22%3A50%7D"


def switch_to_iframe(driver):
    # Switch to iframe
    frame_css = "#try-it > devsite-apix > div > div > iframe"
    WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, frame_css))
    )
    frame = driver.find_element(By.CSS_SELECTOR, frame_css)
    driver.switch_to.frame(frame)

    # Wait for inputs to show
    WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.ID, "part[0]"))
    )


def execute(driver):
    """Execute API request and return (hopefully complete) html response"""
    # Execute
    driver.find_element(By.ID, "execute").click()

    # Switch to raw HTML output
    raw_html_tab_css = "api-response div.mat-tab-label:nth-child(2)"
    WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, raw_html_tab_css))
    )
    driver.find_element(By.CSS_SELECTOR, raw_html_tab_css).click()

    return scrape_api_response(driver)


def html_to_json(html):
    """parse HTML output into json"""
    json_string = clean_response(html)
    try:
        json_result = json.loads(json_string)
    except Exception as e:
        print(e)
        return None
    return json_result



def scrape_channels_info(driver, ids, batch_len=1, comma_separated=False):
    """
    Return dictionary of channel info by channel id.
    - driver: chromedriver instance
    - ids: list of channel ids to get info on
    - batch_len: how many ids to fetch at once, can crash if too many
    - comma_separated: if True, separated batch ids by commas instead of separate input boxes. Is faster but more likely to crash
    """
    channels = {}

    try:
        driver.get(API_URL.format(mode="channels"))

        switch_to_iframe(driver)

        # Enter arguments
        driver.find_element(By.ID, "part[0]").send_keys(API_CHANNELS_PARTS) # Enter parts

        if not comma_separated: # Create input boxes
            for i in range(batch_len):
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.ID, f"id[{i}]"))
                )
                driver.find_element(By.ID, "add_id").click()
        
        driver.find_element(By.CSS_SELECTOR, "label.mat-checkbox-layout").click() # Disable auth
            
        for batch in range(0, len(ids), batch_len):
            if not comma_separated: # Enter id in each box
                for i, id in enumerate(ids[batch:batch+batch_len]):
                    element = driver.find_element(By.ID, f"id[{i}]")
                    element.clear()
                    element.send_keys(id)
            else: # Enter comma-separated list of ids
                id_str = ",".join(ids[batch:batch+batch_len])
                element = driver.find_element(By.ID, f"id[0]")
                element.clear()
                element.send_keys(id_str)

            # Get result in json
            json_result = html_to_json(execute(driver))
            if not json_result:
                continue

            # Parse each channel json into our format
            for item in json_result["items"]:
                channels[item["id"]] = parse_channel_item(item)

    finally:
        driver.quit()
        return channels


def scrape_playlist_info(driver, playlist_ids):
    """
    Return dictionary of video info (excluding statistics) by video id.
    """
    videos = {}

    try:
        driver.get(API_URL.format(mode="playlistItems"))

        switch_to_iframe(driver)
        
        # Enter arguments
        driver.find_element(By.ID, "part[0]").send_keys(API_PLAYLIST_PARTS) # Enter parts
        driver.find_element(By.CSS_SELECTOR, "label.mat-checkbox-layout").click() # Disable auth

        for playlist_id in playlist_ids:
            # Enter playlist id
            element = driver.find_element(By.ID, f"playlistId")
            element.clear()
            element.send_keys(playlist_id)

            # Get result in json
            json_result = html_to_json(execute(driver))
            if not json_result:
                continue

            # Parse each video json into our format
            for item in json_result["items"]:
                videos[item["id"]] = parse_playlist_item(item)

    finally:
        driver.quit()
        return videos


def scrape_videos_basics_by_api(driver, video_ids: List[str]) -> Dict[str, Dict[str,Union[str,dt.datetime]]]:
    """
    Return dictionary of video upload date and title by video id.
    """
    videos = {}

    try:
        driver.get(API_URL.format(mode="videos"))

        switch_to_iframe(driver)
        
        # Enter arguments
        driver.find_element(By.ID, "part[0]").send_keys("snippet") # Enter parts
        driver.find_element(By.CSS_SELECTOR, "label.mat-checkbox-layout").click() # Disable auth

        for vid_id in video_ids:
            # Enter playlist id
            element = driver.find_element(By.ID, f"id[0]")
            element.clear()
            element.send_keys(vid_id)

            # Get result in json string
            json_string = clean_response(execute(driver))

            # Parse the video json into our format
            video_dict = parse_video_item_str(json_string)
            if not video_dict:
                print(f"Couldn't find {vid_id}: might be private [{__file__}]")
                continue
            videos[vid_id] = video_dict
    except Exception as e:
        print("error whilst scraping video info from YouTube api: ", e, f"[{__file__}]")
    finally:
        driver.quit()
        return videos


if __name__ == "__main__":
    scrape_channels_info()
