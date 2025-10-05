from .base import BaseZBACollector
import re
import time
from typing import List, Set
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from ..utils.crawler import CrawlerUtil


class BostonZBACollector(BaseZBACollector):
    def __init__(self):
        super().__init__(
            city="Boston",
            zba_url="https://www.boston.gov/departments/inspectional-services/zoning-board-appeal#reviews",
        )

    def collect_video_urls(self):
        html = CrawlerUtil.fetch_html(self.zba_url)
        print(html)
