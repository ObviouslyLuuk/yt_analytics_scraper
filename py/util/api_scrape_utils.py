# Selenium stuff
# For a custom wait
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


import time
import datetime as dt
from typing import List, Dict, Union


def stitch_strings(str1, str2):
    for offset in range(len(str1)+1):
        length = len(str1[offset:])
        if str1[offset:] == str2[:length]:
            break
    return str1[:offset] + str2


def clean_response(response: str) -> str:
    # Remove HTML tags
    processed = response.replace('<pre class=" CodeMirror-line " role="presentation">', '') \
                    .replace('<span role="presentation" style="padding-right: 0.1px;">', '') \
                    .replace('</span>','').replace('</pre>','\n').replace('<span cm-text="">','').rstrip(" \n\u200b")
                    
    # Remove HTML intro
    processed = "{"+"{".join(processed.split('{')[1:])
    return processed

def parse_channel_item(item: dict) -> Dict[str, Union[str, dt.datetime, int]]:
    return {
        "name":           item["snippet"]["title"],
        "date_of_origin": item["snippet"]["publishedAt"],
        "logo_id":        item["snippet"]["thumbnails"]["default"]["url"].replace("https://yt3.ggpht.com/",'').replace("=s88-c-k-c0x00ffffff-no-rj",''),
        "country":        item["snippet"]["country"] if "country" in item["snippet"] else "unknown",
        "uploads_id":     item["contentDetails"]["relatedPlaylists"]["uploads"],
        "view_count": int(item["statistics"]["viewCount"]),
        "sub_count":  int(item["statistics"]["subscriberCount"]),
        "vid_count":  int(item["statistics"]["videoCount"]),
        "_date_updated": dt.datetime.now().strftime("%Y-%m-%d")
    }

def parse_playlist_item(item) -> Dict[str,Union[str, dt.datetime]]:
    return {
        "id":   item["contentDetails"]["videoId"],
        "datetime": item["contentDetails"]["videoPublishedAt"],
    }

def parse_video_item_str(item_string: str) -> Union[Dict[str,Union[str, dt.datetime]], None]:
    """Extract title and date from json string. Robust because it doesn't try to json.loads"""
    try:
        title = item_string.split('"title": "')[1].split("\n")[0][:-2]
        date_string = item_string.split('"publishedAt": "')[1][:20] # 20 is the length of 2022-10-24T15:00:24Z
        date = dt.datetime.strptime(date_string[:16], "%Y-%m-%dT%H:%M")
    except IndexError:
        return None
    return {
        "title": title,
        "datetime": date,
    }


def scrape_api_response(driver) -> str:
    """Return stitched string of HOPEFULLY complete API response. Unreliable: sometimes it seems lines are skipped"""
    response = ""

    content_css = "#response-raw > div > div.CodeMirror-scroll > div.CodeMirror-sizer > div > div > div > div.CodeMirror-code"

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, content_css))
    )

    while not response.endswith('</span></span></pre>'):
        driver.execute_script("""
            var l = document.querySelectorAll('api-response pre.CodeMirror-line'); 
                    document.querySelectorAll('api-response pre.CodeMirror-line')[l.length-1].scrollIntoView();
        """)

        new_response = driver.execute_script(f"""return document.querySelector("{content_css}").innerHTML""")
        response = stitch_strings(response, new_response)

        time.sleep(.1)

    return response