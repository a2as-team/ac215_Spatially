# Development Plans Collector

This collector gathers development plan documents from a variety of municipal sources.

It is expected that for each city, a collector for that city is implemented.

Currently, the following cities are supported:

- Boston

## Quick Start

Using Docker:
```bash
docker compose run --rm collector
```

If you changed the code, you need to rebuild the container:
```bash
docker compose build collector && docker image prune -f && docker compose run --rm collector
```

Then you can run the collector:
```bash
cd data/collector
source .venv/bin/activate
uv sync
python development_plans/run.py --city <city>
```

## Resources

### Boston
- https://apps.bostonplans.org/recordslibrary/
- For searching zoning text amendments, you can use this link: https://www.bostonplans.org/document-center?searchtext=&searchmode=anyword&doctype=99;&neighborhood=&project=&department=&program=&language=&date=

### Chicago
- https://resources.chicago.gov/zba/Month-Application-Materials/
- https://www.chicago.gov/city/en/depts/dcd/supp_info/community_developmentcommission/march-2024-community-development-commission-hearing.html
- Search using google custom search: "site:chicago.gov "cpc_materials" "2024"
  - Most of the materials are in the CPC_Materials folder (but the directory is not accessible)
- Search "zoning reclassification" in https://chicityclerkelms.chicago.gov/
  - Try to find attachements inside it
  - There seems to also be an api for it (https://api.chicityclerkelms.chicago.gov/#/Matter/GetMatters)