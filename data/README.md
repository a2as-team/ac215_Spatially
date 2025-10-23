# Data 

### Quick Start
If you want to run the entire pipeline, you can run the following command
```bash
docker compose -f docker-compose.dev.yml up
```

### Collector 

If you want to run only the collector

```bash
docker compose -f docker-compose.dev.yml run --rm collector
```

You will be activated into the uv virtual environment and you can run the collector with the following command

Census Collector:
```bash
python census/run.py
```

Development Plans Collector:
```bash
python development_plans/run.py
```

Paper Collector:
```bash
python paper/run.py
```

Zoning Ordinance Collector:
```bash
python zoning_ordinance/run.py
```

If you have made modifications to the collector, you need to rebuild the container

```bash
docker compose -f docker-compose.dev.yml build collector
docker image prune -f
```