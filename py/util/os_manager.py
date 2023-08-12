# Adapted from webdriver-manager library for my own needs

import re
import subprocess
import platform
import sys


class ChromeType(object):
    GOOGLE = "google-chrome"
    GOOGLE_BETA = "google-chrome-beta"
    CHROMIUM = "chromium"
    BRAVE = "brave-browser"
    MSEDGE = "edge"
class OSType(object):
    LINUX = "linux"
    MAC = "mac"
    WIN = "win"
PATTERN = {
    ChromeType.GOOGLE: r"\d+\.\d+\.\d+(\.\d+)?",
    ChromeType.GOOGLE_BETA: r"\d+\.\d+\.\d+(\.\d+)?",
    ChromeType.CHROMIUM: r"\d+\.\d+\.\d+",
    ChromeType.MSEDGE: r"\d+\.\d+\.\d+",
    "brave-browser": r"\d+\.\d+\.\d+(\.\d+)?",
    "firefox": r"(\d+.\d+)",
}



def determine_powershell():
    """Returns "True" if runs in Powershell and "False" if another console."""
    cmd = "(dir 2>&1 *`|echo CMD);&<# rem #>echo powershell"
    with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            shell=True,
    ) as stream:
        stdout = stream.communicate()[0].decode()
    return "" if stdout == "powershell" else "powershell"

def windows_browser_apps_to_cmd(*apps: str) -> str:
    """Create analogue of browser --version command for windows."""
    powershell = determine_powershell()

    # This is a template for powershell script that will return first non-empty
    first_hit_template = """$tmp = {expression}; if ($tmp) {{echo $tmp; Exit;}};"""
    script = "$ErrorActionPreference='silentlycontinue'; " + " ".join(
        first_hit_template.format(expression=e) for e in apps
    )

    return f'{powershell} -NoProfile "{script}"'

def read_version_from_cmd(cmd, pattern):
    with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            shell=True,
    ) as stream:
        stdout = stream.communicate()[0].decode()
        version = re.search(pattern, stdout)
        version = version.group(0) if version else None
    return version




class OperationSystemManager(object):

    def __init__(self, os_type=None):
        self._os_type = os_type

    @staticmethod
    def get_os_name():
        pl = sys.platform
        if pl == "linux" or pl == "linux2":
            return OSType.LINUX
        elif pl == "darwin":
            return OSType.MAC
        elif pl == "win32":
            return OSType.WIN

    @staticmethod
    def get_os_architecture():
        if platform.machine().endswith("64"):
            return 64
        else:
            return 32

    def get_os_type(self):
        if self._os_type:
            return self._os_type
        return f"{self.get_os_name()}{self.get_os_architecture()}"

    @staticmethod
    def is_arch(os_sys_type):
        if '_m1' in os_sys_type:
            return True
        return platform.processor() != 'i386'

    @staticmethod
    def is_mac_os(os_sys_type):
        return OSType.MAC in os_sys_type

    def get_browser_version_from_os(self, browser_type=None):
        """Return installed browser version."""
        cmd_mapping = {
            ChromeType.GOOGLE: {
                OSType.WIN: windows_browser_apps_to_cmd( # Each of these gets a version for a possible install of Chrome
                    r"(Get-Item -Path '$env:PROGRAMFILES\Google\Chrome\Application\chrome.exe').VersionInfo.FileVersion",
                    r"(Get-Item -Path '$env:PROGRAMFILES (x86)\Google\Chrome\Application\chrome.exe').VersionInfo.FileVersion", # Empty
                    r"(Get-Item -Path '$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe').VersionInfo.FileVersion", # Empty
                    r"(Get-ItemProperty -Path Registry::'HKCU\SOFTWARE\Google\Chrome\BLBeacon').version",
                    r"(Get-ItemProperty -Path Registry::'HKLM\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Google Chrome').version",
                ),
            },
            ChromeType.GOOGLE_BETA: {
                OSType.WIN: windows_browser_apps_to_cmd(
                    r"(Get-Item -Path '$env:PROGRAMFILES\Google\Chrome Beta\Application\chrome.exe').VersionInfo.FileVersion",
                    r"(Get-Item -Path '$env:PROGRAMFILES (x86)\Google\Chrome Beta\Application\chrome.exe').VersionInfo.FileVersion", # Empty
                    r"(Get-Item -Path '$env:LOCALAPPDATA\Google\Chrome Beta\Application\chrome.exe').VersionInfo.FileVersion", # Empty
                    r"(Get-ItemProperty -Path Registry::'HKCU\SOFTWARE\Google\Chrome Beta\BLBeacon').version",
                    r"(Get-ItemProperty -Path Registry::'HKLM\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Google Chrome Beta').version",
                ),
            },
        }

        try:
            cmd_mapping = cmd_mapping[browser_type][OperationSystemManager.get_os_name()]
            pattern = PATTERN[browser_type]
            version = read_version_from_cmd(cmd_mapping, pattern)
            return version
        except Exception as e:
            print("Exception: ", e)
            return None
            # raise Exception("Can not get browser version from OS")

