import csv
import datetime as dt
import os
from urllib.request import urlopen
import scrapetube

# Selenium stuff
from selenium import webdriver
from selenium.common.exceptions import TimeoutException

from typing import List, Dict, Union

from .helpers import startWebdriver, extract_from_str, wait_for_element

from .custom_values import CHANNEL_ID, DATA_DIR
from .constants import VIDEOS_URL, VIDEO_URL

from .api_scrape import scrape_videos_basics_by_api


def scrape_recent_video_ids(driver, upload_or_live="live"):
    """Return list of recent video ids. upload_or_live can be upload or live. live actually finds all video ids, not just lives, for some reason."""
    driver.get(VIDEOS_URL.format(channel_id=CHANNEL_ID, upload_or_live=upload_or_live))

    wait_for_element(driver, "ytcp-video-list-cell-video")
    return driver.execute_script('return Array.from(document.querySelectorAll("ytcp-video-list-cell-video")).map((e)=>{return e.__data.video.videoId})')

def scrape_recent_video_ids_by_scrapetube(logged_ids: list):
    """Return list of recent video ids. Use scrapetube to scrape the video ids."""
    videos = scrapetube.get_channel(CHANNEL_ID)
    new_ids = []
    for video in videos:
        if video["videoId"] in logged_ids:
            break
        new_ids.append(video['videoId'])
    return new_ids

def adjust_video_log(datetime: dt.datetime, id: str, title: str, recent: int=1, precise: int=0) -> None:
    """
    Reads videos from video log, adds given arguments (either adding a new video, 
    or adjusting an existing one), and then overwrites the video log.
    """
    try:
        with open(DATA_DIR+"video_log.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            videos = []
            for video in reader:
                if video["id"] == id:
                    print(f"video already in log, overwriting entry [{__file__}]")
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
        "precise": precise
    })
    videos.sort(key=lambda video: dt.datetime.strptime(video["date"], '%Y-%m-%d %H:%M'))

    with open(DATA_DIR+"video_log.csv", "w", newline='', encoding="utf-8") as f:
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
        with open(DATA_DIR+"video_log.csv", "r", encoding="utf-8") as f:
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
        print(f"No video log found: created one [{__file__}]")
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
    logged_videos = {video["id"]: video for video in logged_videos}

    # Scrape video ids if not given
    driver = startWebdriver()
    try:
        # No new videos if the video ids were already in the log
        logged_video_ids = [vid["id"] for vid in logged_videos.values()]

        if not video_ids:
            try:
                video_ids = scrape_recent_video_ids_by_scrapetube(logged_video_ids)
            except Exception as e:
                print(e)
                print("Falling back to scraping by YouTube Studio")
                video_ids = scrape_recent_video_ids(driver)

        # Only scrape videos that aren't in the log
        video_ids = [id for id in video_ids if id not in logged_video_ids]
        # Add videos that don't have precise datetime
        video_ids += [id for id, video in logged_videos.items() if video["precise"] == "0"]
        if not video_ids:
            driver.quit()
            print(f"No new videos")
            return
        
        # Scrape title and datetime and add video
        videos = scrape_videos_basics(driver, video_ids)
        for id, dict in videos.items():
            # dict sometimes contains characters that map to undefined, unless utf-8 encoding is used
            enc_dict = {k: v.encode('utf-8') if type(v)==str else v for k, v in dict.items()}
            print(f"Adding new video to log: {enc_dict}")
            adjust_video_log(dict["datetime"], id, dict["title"], precise=dict["precise"])
    finally:
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
                precise=video["precise"],
            )
            print(f"updated recency of {video['id']} to False")


def scrape_videos_basics(driver, video_ids: List[str]) -> Dict[str, Dict[str,Union[str,dt.datetime]]]:
    """
    Return dictionary of video upload date and title by video id. Uses API if possible, otherwise scrapes video page with less precise upload date.
    """
    try:
        # videos = scrape_videos_basics_by_api(driver, video_ids)
        raise Exception("Skipping API call (quota exceeded?)")
    except Exception as e:
        print(e)
        print("Falling back to scraping by YouTube DataViewer")
        try:
            videos = scrape_videos_basics_by_dataviewer(driver, video_ids)
            # raise Exception("Skipping YouTube DataViewer (stuck)")
        except Exception as e:
            print(e)
            print("Falling back to extracting by video page")
            videos = extract_videos_basics_by_page(video_ids)
    return videos


def scrape_videos_basics_by_page(driver, video_ids):
    """
    Return dictionary of video upload date and title by video id. Uses video page and cannot get precise upload time.
    """
    videos = {}

    for video_id in video_ids:
        driver.get(VIDEO_URL.format(video_id=video_id))

        # Wait for page to load
        wait_for_element(driver, "meta[itemprop='uploadDate']")

        # Execute script to get upload date and title
        videos[video_id] = driver.execute_script("""return {
            datetime: document.querySelector("meta[itemprop='uploadDate']").content, 
            title: document.querySelector("meta[itemprop='name']").content}""")
        # Not actually datetime, just date, but we save it as datetime for consistency
        videos[video_id]["datetime"] = dt.datetime.strptime(videos[video_id]["datetime"], '%Y-%m-%d')
        videos[video_id]["precise"] = 0

    return videos


def extract_videos_basics_by_page(video_ids: List[str]) -> Dict[str, Dict[str,Union[str,dt.datetime]]]:
    """
    Return dictionary of video upload date and title by video id. Uses video page and cannot get precise upload time. Most robust since it only relies on urlopen.
    """
    videos = {}

    for video_id in video_ids:
        title, date = extract_video_basics_by_page(video_id)
        if not title or not date:
            print(f"Couldn't extract video basics for {video_id}, might be private")
            continue
        videos[video_id] = {"title": title, "datetime": date, "precise": 0}
    return videos


def extract_video_basics_by_page(id: str) -> tuple:
    """Use video page to extract video datetime. Uses urlopen. Return (title, datetime)"""
    with urlopen(VIDEO_URL.format(video_id=id)) as f:
        html = f.read().decode("utf8")
    
    title = extract_from_str(html, '<meta itemprop="name" content="',       '"><meta ')
    assert len(title) <= 100, f"Found title length is {len(title)} chars long, should be between 1 and 100"
    date  = extract_from_str(html, '<meta itemprop="uploadDate" content="', '"><meta ')
    assert len(date) <= 10, f"Found date length is {len(date)} chars long, should be 10"
    if not title or not date:
        return (None, None)
    date = dt.datetime.strptime(date, '%Y-%m-%d')
    return (title, date)


def scrape_videos_basics_by_dataviewer(driver, video_ids: List[str]) -> Dict[str, Dict[str,Union[str,dt.datetime]]]:
    """
    Return dictionary of video upload date and title by video id. Uses https://citizenevidence.amnestyusa.org/ (YouTube DataViewer) and gets precise upload time.
    Fairly often the page gets stuck and gives a TimeoutException.
    """
    videos = {}

    for video_id in video_ids:
        title, datetime = scrape_video_basics_by_dataviewer(driver, video_id)
        videos[video_id] = {"title": title, "datetime": datetime, "precise": 1}
    return videos


def scrape_video_basics_by_dataviewer(driver, video_id: str) -> tuple:
    """Use https://citizenevidence.amnestyusa.org/ (YouTube DataViewer) to scrape video datetime. Return (title, datetime)
    Fairly often the page gets stuck and gives a TimeoutException."""
    # Get upload date and time (UTC)
    driver.get("https://citizenevidence.amnestyusa.org/")

    # Wait 10 seconds for the input element to show up
    input = wait_for_element(driver, "#formInput")
    input.send_keys(f"www.youtube.com/watch?v={video_id}")
    driver.find_element_by_css_selector('#formInputButton').click()

    # Wait 10 seconds for the output text to show up
    try:
        wait_for_element(driver, '#shortOutput > strong')
    except TimeoutException as e:
        raise TimeoutException(f"Amnesty page stuck")
    title = driver.find_element_by_css_selector('#shortOutput > span > a').get_attribute('innerText')
    output_elem = driver.find_element_by_css_selector('#shortOutput')
    output_string = output_elem.get_attribute('innerText')
    date_string = output_string.split('Upload Date (YYYY/MM/DD): ')[-1].split('\n')[0]
    time_string = output_string.split('Upload Time (UTC): ')[-1].split(' (')[0]
    datetime = dt.datetime.strptime(date_string+' '+time_string[0:-3], '%Y-%m-%d %H:%M')

    return title, datetime
