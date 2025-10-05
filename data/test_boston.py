from collector.utils.crawler import CrawlerUtil
import re

soup = CrawlerUtil.crawl('https://www.boston.gov/departments/inspectional-services/zoning-board-appeal#reviews')
heading = soup.find(string=re.compile(r'Full Board Meeting Videos', re.IGNORECASE))
h2 = heading.find_parent()
parent_div = h2.find_parent()

print(f"Parent div: {parent_div.name}, class: {parent_div.get('class')}")

# Look for YouTube links in parent div
youtube_links = []
for link in parent_div.find_all('a', href=True):
    if 'youtube' in link['href']:
        youtube_links.append(link['href'])

print(f"Found {len(youtube_links)} YouTube links in parent div")

# Try going up one more level
grandparent = parent_div.find_parent()
print(f"\nGrandparent: {grandparent.name}, class: {grandparent.get('class')}")

youtube_links_gp = []
for link in grandparent.find_all('a', href=True):
    if 'youtube' in link['href']:
        youtube_links_gp.append(link['href'])

print(f"Found {len(youtube_links_gp)} YouTube links in grandparent")
if youtube_links_gp:
    print("First few links:")
    for link in youtube_links_gp[:3]:
        print(f"  {link}")
