from util.custom_values import DATA_DIR
from util.constants import ScrapeMode
from scrape_hourly import process
import os

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
        process(mode, string=string, dir=DATA_DIR)

if __name__ == "__main__":
    pass_strings(ScrapeMode.video, "EnergyStuck", DATA_DIR+"data\\")
    pass_strings(ScrapeMode.channel, "total", DATA_DIR+"data\\")
