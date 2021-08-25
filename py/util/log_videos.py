import csv
import datetime as dt
import os

# Selenium stuff
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .helpers import startWebdriver

from .custom_values import CHANNEL_ID, DATA_DIR
from .constants import ANALYTICS_URL


def scrape_recent_video_id(driver: webdriver.Chrome) -> str:
    driver.get(ANALYTICS_URL.format(mode="channel", id=CHANNEL_ID))

    # Get video_id of the most recent video from link on page
    link_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//a[@class='remove-default-style style-scope yta-video-snapshot-carousel']"))
    )
    link_string = link_element.get_attribute('href')
    video_id = link_string.split('/')[-4]    
    return video_id


def scrape_date_time(driver: webdriver.Chrome, video_id: str) -> tuple:
    # Get upload date and time (UTC)
    driver.get("https://citizenevidence.amnestyusa.org/")

    # Wait 10 seconds for the input element to show up
    input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#formInput"))
    )
    input.send_keys(f"www.youtube.com/watch?v={video_id}")
    driver.find_element_by_css_selector('#formInputButton').click()

    # Wait 10 seconds for the output text to show up
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '#shortOutput > strong'))
    )
    title = driver.find_element_by_css_selector('#shortOutput > span > a').get_attribute('innerText')
    output_elem = driver.find_element_by_css_selector('#shortOutput')
    output_string = output_elem.get_attribute('innerText')
    date_string = output_string.split('Upload Date (YYYY/MM/DD): ')[-1].split('\n')[0]
    time_string = output_string.split('Upload Time (UTC): ')[-1].split(' (')[0]
    datetime = dt.datetime.strptime(date_string+' '+time_string[0:-3], '%Y-%m-%d %H:%M')

    return title, datetime


def adjust_video_log(datetime: dt.datetime, id: str, title: str, recent: int=1) -> None:
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


def get_videos(recent: bool=True) -> list:
    """
    Return a list of videos from the offline log.

    Parameters
    ----------
    recent : bool, optional
        True only gives videos where recent == 1

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
                if recent and int(video["recent"]) != 1:
                    continue
                video["date"] = dt.datetime.strptime(
                    video["date"], '%Y-%m-%d %H:%M')
                videos.append(video)
    except FileNotFoundError:
        update_video_log()
        print("No video log found: created one")
        videos = get_videos(recent)

    return videos


def update_video_log(video_id: str='') -> None:
    # Get videos already in log
    videos = []
    if os.path.isfile(DATA_DIR+"video_log.csv"):
        videos = get_videos(False)

    # Scrape video id if not given
    driver = startWebdriver()
    if not video_id:
        video_id = scrape_recent_video_id(driver)

    # No new videos if the video id was already in the log
    if video_id in [video["id"] for video in videos]:
        driver.quit()
        print("No new videos")
        return
    
    # Scrape title and datetime and add video
    title, datetime = scrape_date_time(driver, video_id)
    adjust_video_log(datetime, video_id, title)
    print("Added new video to log")
    driver.quit()
