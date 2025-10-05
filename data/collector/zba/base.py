from abc import ABC, abstractmethod
import time

import requests


class BaseZBACollector(ABC):
    city = ""
    zba_url = ""

    def __init__(self, city: str, zba_url: str):
        self.city = city
        self.zba_url = zba_url
        if not self.city:
            raise ValueError("City is required")
        if not self.zba_url:
            raise ValueError("ZBA URL is required")

    @abstractmethod
    def collect_video_urls(self):
        """
        This should go into the zba url and find the video urls since the zbas are best informed by the video recordings.
        We should use bs4 or selenium to find the video urls.
        """
        pass

    def _transcribe_video_urls(self):
        """
        This should go into the video urls and transcribe the videos.
        """
        pass

    def collect(self):
        self.collect_video_urls()
        self._transcribe_video_urls()
