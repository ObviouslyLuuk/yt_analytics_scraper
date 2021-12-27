from util.custom_values import DATA_DIR
from util.constants import ScrapeMode, CHANNEL_ID
from scrape_hourly import parse_string, init_date, assemble_data, save_data
import os

def process_string(mode: ScrapeMode=ScrapeMode.channel, 
dir: str='', string: str='') -> None:
    """Weaves all basic functionality together"""
    # Process string
    card_obj = parse_string(string)
    id = CHANNEL_ID
    if mode == ScrapeMode.video:
        id = card_obj \
            ["exploreConfig"]["restrictAndTimePeriodConfig"]["entity"]["id"]

    date_dict = init_date(card_obj["lastUpdated"])

    data = assemble_data(card_obj, date_dict, mode)
    save_data(data, f"Hourly_{id}", dir)


def pass_strings(mode: ScrapeMode, name: str, dir: str='') -> None:
    """
    Parse strings and save to csv. Meant to go through text files
    containing the mini-card attribute as a string instead of
    scraping it.

    Parameters
    ----------
    mode : ScrapeMode
        Either ScrapeMode.channel or ScrapeMode.video.
    name : str
        Common part of the filenames that contain either the
        channel data or data for a video.
        Example:
            Total_21-08-12
            Total_21-08-14
            Total_21-08-16
        Would be "Total"
    dir : str
        The directory that contains the textfiles.
    """
    filenames = os.listdir(dir)
    for filename in filenames:
        if name not in filename:
            continue

        with open(dir+filename, "r") as f:
            string = f.read()
        print(f"Parsing file: {filename}")
        process_string(mode, string=string, dir=DATA_DIR)

if __name__ == "__main__":
    pass_strings(ScrapeMode.video, "EnergyStuck", DATA_DIR+"data\\")
    pass_strings(ScrapeMode.channel, "total", DATA_DIR+"data\\")
