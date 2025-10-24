# Data 

### Quick Start
If you want to run the entire pipeline, you can run the following command
```bash
docker compose up
```

### Collector 

If you want to run only the collector

```bash
docker compose run --rm collector
```

You will be activated into the uv virtual environment and you can run the collector with the following command

Census Collector:
```bash
python collector/census/run.py
```

Development Plans Collector:
```bash
python collector/development_plans/run.py
```

Paper Collector:
```bash
python collector/paper/run.py
```

Zoning Ordinance Collector:
```bash
python collector/zoning_ordinance/run.py
```

If you have made modifications to the collector, you need to rebuild the container

```bash
docker compose -f build collector && docker image prune -f && docker compose run --rm collector
```