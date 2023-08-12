# Adapted from webdriver-manager library for my own needs

import os
from typing import Optional

from packaging import version
from webdriver_manager.core.download_manager import DownloadManager, WDMDownloadManager
from webdriver_manager.core.driver_cache import DriverCacheManager

from .os_manager import OperationSystemManager, ChromeType

LATEST_RELEASE_URL = "https://chromedriver.storage.googleapis.com/LATEST_RELEASE"
RELEASE_URL = "https://chromedriver.storage.googleapis.com"
NAME = "chromedriver"



class ChromeDriver(object):
    def __init__(
            self,
            name,
            chrome_type,
            http_client,
            os_system_manager):
        self._name = name
        self._http_client = http_client
        self._browser_version = None
        self._os_system_manager = os_system_manager
        self._browser_type = chrome_type
        if not self._os_system_manager:
            self._os_system_manager = OperationSystemManager()

    def get_name(self):
        return self._name
    def get_browser_type(self):
        return self._browser_type

    def get_browser_version_from_os(self):
        """
        Use-cases:
        - for key in metadata;
        - for printing nice logs;
        - for fallback if version was not set at all.
        Note: the fallback may have collisions in user cases when previous browser was not uninstalled properly.
        """
        if self._browser_version is None:
            self._browser_version = self._os_system_manager.get_browser_version_from_os(self._browser_type)
        return self._browser_version

    def get_binary_name(self, os_type):
        driver_binary_name = (
            "msedgedriver" if self._name == "edgedriver" else self._name
        )
        driver_binary_name = (
            f"{driver_binary_name}.exe" if "win" in os_type else driver_binary_name
        )
        return driver_binary_name

    def get_driver_download_url(self, os_type):
        driver_version_to_download = self.get_driver_version_to_download()
        # 115.0.5763.0 is the first version that has the chromedriver url in the known-good-versions-with-downloads.json
        if version.parse(driver_version_to_download) >= version.parse("115.0.5763.0"):
            return self.get_url_for_version_and_platform(driver_version_to_download, os_type)
        return f"{RELEASE_URL}/{driver_version_to_download}/{self._name}_{os_type}.zip"

    def get_latest_release_version(self):
        """Return the latest release version of the driver"""
        resp = self._http_client.get(url=LATEST_RELEASE_URL)
        return resp.text.rstrip()

    def get_driver_version_to_download(self):
        return self.get_browser_version_from_os()

    def get_url_for_version_and_platform(self, browser_version, platform):
        url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
        response = self._http_client.get(url)
        data = response.json()
        versions = data["versions"]

        short_version = ".".join(browser_version.split(".")[:3])
        compatible_versions = [v for v in versions if short_version in v["version"]]
        if compatible_versions:
            latest_version = compatible_versions[-1]
            downloads = latest_version["downloads"]["chromedriver"]
            for d in downloads:
                if d["platform"] == platform:
                    return d["url"]

        raise Exception(f"No such driver version {browser_version} for {platform}")



class ChromeDriverManager(object):
    def __init__(
            self,
            name: str = "chromedriver",
            chrome_type: str = ChromeType.GOOGLE_BETA,
            download_manager: Optional[DownloadManager] = None,
            cache_manager: Optional[DriverCacheManager] = None,
            os_system_manager: Optional[OperationSystemManager] = None
    ):
        self._cache_manager = cache_manager
        if not self._cache_manager:
            self._cache_manager = DriverCacheManager()

        self._download_manager = download_manager
        if self._download_manager is None:
            self._download_manager = WDMDownloadManager()

        self._os_system_manager = os_system_manager
        if not self._os_system_manager:
            self._os_system_manager = OperationSystemManager()

        self.driver = ChromeDriver(
            name=name,
            chrome_type=chrome_type,
            http_client=self.http_client,
            os_system_manager=os_system_manager
        )

    @property
    def http_client(self):
        return self._download_manager.http_client

    def get_os_type(self):
        """Return the os type of the current os, either 'win32', 'mac_arm64' or a mac_os type"""
        os_type = self._os_system_manager.get_os_type()
        if "win" in os_type:
            return "win32"

        if not self._os_system_manager.is_mac_os(os_type):
            return os_type

        if self._os_system_manager.is_arch(os_type):
            return "mac_arm64"

        return os_type

    def _get_driver_binary_path(self, driver):
        """Return the path of the binary file of the driver. A binary file is a file that can be executed by the os"""
        # In case the driver is already cached, return the path of the cached driver
        binary_path = self._cache_manager.find_driver(driver)
        if binary_path:
            return binary_path

        os_type = self.get_os_type()
        file = self._download_manager.download_file(driver.get_driver_download_url(os_type))
        binary_path = self._cache_manager.save_file_to_cache(driver, file)
        return binary_path
    
    def install(self) -> str:
        """Return the path of the binary file of the driver after making it executable"""
        driver_path = self._get_driver_binary_path(self.driver)
        os.chmod(driver_path, 0o755) # make executable, 0o755 is the octal representation of the permissions
        return driver_path
