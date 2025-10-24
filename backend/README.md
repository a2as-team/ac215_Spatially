# Backend

Reference: https://github.com/fastapi/full-stack-fastapi-template/tree/master

## How to run the project through Docker

```bash
docker build -t spatially-api .
docker run --rm -p 8000:8000 spatially-api
```

## How to run the project through Uvicorn

```bash
uv run uvicorn app.main:app --reload
```