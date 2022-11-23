import csv
import datetime as dt
import os

# Selenium stuff
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from typing import List, Dict, Union

from .helpers import startWebdriver

from .custom_values import CHANNEL_ID, DATA_DIR
from .constants import VIDEOS_URL

from .api_scrape import scrape_videos


def scrape_recent_video_ids(driver, upload_or_live="live"):
    """Return list of recent video ids. upload_or_live can be upload or live. live actually finds all video ids, not just lives, for some reason."""
    driver.get(VIDEOS_URL.format(channel_id=CHANNEL_ID, upload_or_live=upload_or_live))

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "ytcp-video-list-cell-video"))
    )
    return driver.execute_script('return Array.from(document.querySelectorAll("ytcp-video-list-cell-video")).map((e)=>{return e.__data.video.videoId})')


def adjust_video_log(datetime: dt.datetime, id: str, title: str, recent: int=1) -> None:
    """
    Reads videos from video log, adds given arguments (either adding a new video, 
    or adjusting an existing one), and then overwrites the video log.
    """
    try:
        with open(DATA_DIR+"video_log.csv", "r") as f:
            reader = csv.DictReader(f)
            videos = []
            for video in reader:
                if video["id"] == id:
                    print("video already in log, overwriting entry")
                    continue
                videos.append(video)
    except FileNotFoundError:
        print("Making new video log file")
        videos = []

    videos.append({
        "date": datetime.strftime('%Y-%m-%d %H:%M'),
        "id": id,
        "title": title,
        "recent": recent,
    })
    videos.sort(key=lambda video: dt.datetime.strptime(video["date"], '%Y-%m-%d %H:%M'))

    with open(DATA_DIR+"video_log.csv", "w", newline='') as f:
        writer = csv.DictWriter(f, videos[0].keys())
        writer.writeheader()
        writer.writerows(videos)


def get_videos(only_recent: bool=True) -> list:
    """
    Return a list of videos from the offline log.

    Parameters
    ----------
    only_recent : bool, optional
        True only gives videos where recent == 1,
        this is when the video is younger than a month,
        after that timeframe YouTube disables the hourly view.

    Returns
    -------
    list
        {
            "date": dt.datetime,
            "id": video id,
            "title": video title,
            "recent": whether new hourly data is still being logged
        }
    """
    try:
        with open(DATA_DIR+"video_log.csv", "r") as f:
            reader = csv.DictReader(f)
            videos = []
            for video in reader:
                if only_recent and int(video["recent"]) != 1:
                    continue
                video["date"] = dt.datetime.strptime(
                    video["date"], '%Y-%m-%d %H:%M')
                videos.append(video)
    except FileNotFoundError:
        update_video_log()
        print("No video log found: created one")
        videos = get_videos(only_recent)

    return videos


def update_video_log(video_ids: List[str]=[]) -> None:
    """
    Scrapes video metadata and calls adjust_video_log to update the log.
    Also calls update_video_log_recencies
    """
    # Get videos already in log
    logged_videos = []
    if os.path.isfile(DATA_DIR+"video_log.csv"):
        logged_videos = get_videos(False)

    # Scrape video ids if not given
    driver = startWebdriver()
    if not video_ids:
        video_ids = scrape_recent_video_ids(driver)

    # No new videos if the video ids were already in the log
    logged_video_ids = [vid["id"] for vid in logged_videos]
    print(video_ids)
    video_ids = [id for id in video_ids if id not in logged_video_ids]
    if not video_ids:
        driver.quit()
        print("No new videos")
        return
    
    # Scrape title and datetime and add video
    videos = scrape_videos(driver, video_ids)
    for id, dict in videos.items():
        print(f"Adding new video to log: {dict}")
        adjust_video_log(dict["datetime"], id, dict["title"])
    driver.quit()

    update_video_log_recencies(get_videos(True))


def update_video_log_recencies(videos, days=31):
    """
    Iterate through videos in log and check if they're still younger than <days>.
    Default is 31 days because YouTube turns off hourly data after a month.
    """
    for video in videos:
        recent = dt.datetime.utcnow() - video['date'] < dt.timedelta(days=days)

        if int(video["recent"]) and not recent:
            adjust_video_log(
                video["date"],
                video["id"],
                video["title"],
                recent=0,
            )
            print(f"updated recency of {video['id']} to False")
