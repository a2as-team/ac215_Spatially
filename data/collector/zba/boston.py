from .base import BaseZBACollector
import re
import time
from typing import List, Set, Dict
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

    def collect_video_urls(self) -> Dict[str, str]:
        """
        Collects video URLs from the Full Board Meeting Videos section.

        Returns:
            Dict[str, str]: Dictionary mapping date strings to YouTube URLs
        """
        soup = CrawlerUtil.crawl(self.zba_url)
        if not soup:
            return {}

        video_data = {}

        # Find the "Full Board Meeting Videos" section
        heading = soup.find(
            string=re.compile(r"Full Board Meeting Videos", re.IGNORECASE)
        )
        if not heading:
            return video_data

        # Get the parent container that holds the videos
        # Traverse up until we find a parent with YouTube links
        section = heading.find_parent()
        while section:
            youtube_links = [
                link
                for link in section.find_all("a", href=True)
                if "youtube.com/watch" in link["href"] or "youtu.be/" in link["href"]
            ]
            if youtube_links:
                break
            section = section.find_parent()

        if not section:
            return video_data

        # Find all YouTube links within this section
        for link in section.find_all("a", href=True):
            href = link["href"]
            if "youtube.com/watch" in href or "youtu.be/" in href:
                # Extract video ID and normalize URL
                video_id = None
                if "youtube.com/watch?v=" in href:
                    video_id = href.split("watch?v=")[1].split("&")[0]
                elif "youtu.be/" in href:
                    video_id = href.split("youtu.be/")[1].split("?")[0]

                if video_id:
                    normalized_url = f"https://www.youtube.com/watch?v={video_id}"

                    # Extract date from link text
                    link_text = link.get_text(strip=True)
                    # Pattern: "Boston Zoning Board of Appeal Hearing: Month Day, Year part X"
                    date_match = re.search(
                        r"([A-Z][a-z]+\s+\d{1,2},\s+\d{4})", link_text
                    )
                    if date_match:
                        date_str = date_match.group(1)
                        # Handle multiple parts on same date
                        if date_str in video_data:
                            # Append as list if multiple videos for same date
                            if isinstance(video_data[date_str], list):
                                if normalized_url not in video_data[date_str]:
                                    video_data[date_str].append(normalized_url)
                            else:
                                if normalized_url != video_data[date_str]:
                                    video_data[date_str] = [
                                        video_data[date_str],
                                        normalized_url,
                                    ]
                        else:
                            video_data[date_str] = normalized_url

        return video_data
