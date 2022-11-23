import os

# CUSTOM VALUES ---------------------------------------------------------------

CHANNEL_ID          = "UChXogayC52mlROq-N71_f5g"
PLAYLIST_ID         = "UUhXogayC52mlROq-N71_f5g" # Playlist with all the channel's videos
# This is where the csv data files will appear
DATA_DIR            = "D:\\Users\\Luuk\\Documents\\Programming\\stuff\\yt_realtime_data\\"
# This is the location where you put a chromedriver
# (you'll need to download one that corresponds to your version of Google Chrome)
CHROMEDRIVER_PATH   = "C:\\chromedriver\\chromedriver"
# Find the "User Data" folder at
# C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data\\
USER_DATA_PATH     = os.path.join(DATA_DIR, "User Data")
# CHROME_PROFILES     = "C:\\Users\\321lu\\AppData\\Local\\Google\\Chrome\\User Data\\"
# Use a profile that's already logged in to the desired YouTube channel
CHROME_PROFILE      = "Profile 1"

USER_DATA_BACKUP_PATH = os.path.join(DATA_DIR, "backup/User Data(backup)")

if __name__ == "__main__":
    print()
    print(f"data listdir: {os.listdir(DATA_DIR)}")
    print()
    print(f"chromedriver listdir: {os.listdir(os.path.dirname(CHROMEDRIVER_PATH))}")
    print()
    print(f"user data listdir: {os.listdir(USER_DATA_PATH)}")