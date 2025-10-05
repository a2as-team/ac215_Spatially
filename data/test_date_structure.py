from collector.utils.crawler import CrawlerUtil
import re

soup = CrawlerUtil.crawl('https://www.boston.gov/departments/inspectional-services/zoning-board-appeal#reviews')
heading = soup.find(string=re.compile(r'Full Board Meeting Videos', re.IGNORECASE))

# Find the section with YouTube links
section = heading.find_parent()
while section:
    youtube_links = [link for link in section.find_all("a", href=True)
                   if "youtube.com/watch" in link["href"] or "youtu.be/" in link["href"]]
    if youtube_links:
        break
    section = section.find_parent()

# Look at the first few links and their context
for i, link in enumerate(youtube_links[:5]):
    print(f"\n--- Link {i+1} ---")
    print(f"URL: {link['href']}")
    print(f"Link text: {link.get_text(strip=True)}")

    # Check parent structure
    parent = link.find_parent()
    print(f"Parent: {parent.name}, text: {parent.get_text(strip=True)[:100]}")
