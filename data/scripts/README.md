# Dynamic Entry Point Scripts

Three simple, reusable scripts for running collectors and parsers with environment variables.

## Philosophy

**Keep it simple:**
- ✅ Only 3 generic scripts (not 10+ city-specific scripts)
- ✅ Configuration in docker-compose.yml (easy to see and change)
- ✅ Environment variables for flexibility
- ✅ Easy to manage and understand

## The 3 Scripts

```
scripts/
├── run-collector.sh              # Generic collector runner
├── run-parser.sh                 # Generic parser runner
```

That's it! All configuration is in `docker-compose.yml`.

## How It Works

### docker-compose.yml (Configuration)

```yaml
dev-plans-collector:
  environment:
    - COLLECTOR_NAME=development_plans  # Which collector to run
    - CITY=boston                       # Which city
  command: /app/scripts/run-collector.sh

dev-plans-parser:
  environment:
    - PARSER_NAME=development_plans     # Which parser to run
    - CITY=boston                       # Which city
    - MODEL=llama3.2                    # Which model
  command: /app/scripts/run-parser-with-ollama.sh
```

### Generic Script (Reads Environment Variables)

```bash
# run-collector.sh
COLLECTOR_NAME=$COLLECTOR_NAME  # Read from environment
CITY=$CITY                      # Read from environment

# Run the collector
uv run python collector/${COLLECTOR_NAME}/run.py --city $CITY
```

## Usage

### Run with Default Configuration

```bash
# Configuration is in docker-compose.yml
docker compose up dev-plans-collector
docker compose up dev-plans-parser
```

### Change City (Override at Runtime)

```bash
# No file changes needed!
docker compose run -e CITY=cambridge dev-plans-collector
docker compose run -e CITY=cambridge dev-plans-parser
```

### Change Model

```bash
docker compose run -e MODEL=llama3.1 dev-plans-parser
```

### Change Multiple Variables

```bash
docker compose run \
  -e CITY=cambridge \
  -e MODEL=mistral \
  dev-plans-parser
```

## Available Scripts

### `run-collector.sh`

Generic collector entry point.

**Required Environment Variables:**
- `COLLECTOR_NAME` - Name of collector (census, development_plans, zba)

**Optional Environment Variables:**
- `CITY` - City to collect (for development_plans)
- `CENSUS_TYPE` - Census type (for census collector, default: acs5)
- `LEVEL` - Geographic level (for census collector, default: tract)

**Example:**
```yaml
census-collector:
  environment:
    - COLLECTOR_NAME=census
    - CENSUS_TYPE=acs5
    - LEVEL=tract
  command: /app/scripts/run-collector.sh

dev-plans-collector:
  environment:
    - COLLECTOR_NAME=development_plans
    - CITY=boston
  command: /app/scripts/run-collector.sh
```

### `run-parser.sh`

Generic parser for use with host Ollama (recommended for development).

**Required Environment Variables:**
- `PARSER_NAME` - Name of parser (development_plans)

**Optional Environment Variables:**
- `CITY` - City to parse
- `MODEL` - Model to use (default: llama3.2)

**Example:**
```yaml
dev-plans-parser-host:
  environment:
    - PARSER_NAME=development_plans
    - CITY=boston
    - MODEL=llama3.2
    - OLLAMA_HOST=http://host.docker.internal:11434
  command: /app/scripts/run-parser.sh
```

### `run-parser-with-ollama.sh`

Generic parser that waits for Ollama and pulls models automatically.

**Required Environment Variables:**
- `PARSER_NAME` - Name of parser

**Optional Environment Variables:**
- `CITY` - City to parse
- `MODEL` - Model to use (default: llama3.2)
- `OLLAMA_HOST` - Ollama endpoint (default: http://ollama:11434)

**Features:**
- Waits up to 30 seconds for Ollama to be ready
- Automatically pulls the specified model
- Shows clear status messages

**Example:**
```yaml
dev-plans-parser:
  depends_on:
    - ollama
  environment:
    - PARSER_NAME=development_plans
    - CITY=boston
    - MODEL=llama3.2
    - OLLAMA_HOST=http://ollama:11434
  command: /app/scripts/run-parser-with-ollama.sh
```

## Adding New Cities

Just add a new service to docker-compose.yml with different environment variables:

```yaml
# Boston (existing)
boston-collector:
  environment:
    - COLLECTOR_NAME=development_plans
    - CITY=boston
  command: /app/scripts/run-collector.sh

# Cambridge (new!)
cambridge-collector:
  environment:
    - COLLECTOR_NAME=development_plans
    - CITY=cambridge  # Just change this!
  command: /app/scripts/run-collector.sh

# Somerville (new!)
somerville-collector:
  environment:
    - COLLECTOR_NAME=development_plans
    - CITY=somerville  # Just change this!
  command: /app/scripts/run-collector.sh
```

**No new scripts needed!** Same 3 generic scripts handle all cities.

## Local Testing

Scripts work locally too:

```bash
cd data
source .venv/bin/activate

# Run collector locally
COLLECTOR_NAME=development_plans CITY=boston ./scripts/run-collector.sh

# Run parser locally (with Ollama running)
ollama serve  # Terminal 1
PARSER_NAME=development_plans CITY=boston MODEL=llama3.2 ./scripts/run-parser.sh  # Terminal 2
```

## Benefits

✅ **Simple** - Only 3 scripts to maintain
✅ **Flexible** - Change city/model via environment variables
✅ **Visible** - All config in docker-compose.yml
✅ **Reusable** - Same scripts for all cities
✅ **Overrideable** - Runtime overrides with `-e`
✅ **Testable** - Works both in Docker and locally

## Comparison

### ❌ Too Many Scripts (Bad)

```
scripts/
├── run-census-collector.sh
├── run-boston-collector.sh
├── run-cambridge-collector.sh
├── run-somerville-collector.sh
├── run-boston-parser.sh
├── run-cambridge-parser.sh
├── run-somerville-parser.sh
└── ... 20+ scripts
```

**Problems:**
- Hard to maintain
- Duplicate code everywhere
- Need new script for each city

### ✅ Generic Scripts with Environment Variables (Good)

```
scripts/
├── run-collector.sh              # Handles ALL collectors
├── run-parser.sh                 # Handles ALL parsers
└── run-parser-with-ollama.sh     # Parser with Ollama setup
```

**Benefits:**
- Easy to maintain
- No duplicate code
- Add cities via docker-compose.yml only

## Best Practices

1. **Keep scripts generic** - Don't create city-specific scripts
2. **Use environment variables** - Configure in docker-compose.yml
3. **Override at runtime** - Use `-e` for testing different configs
4. **Test locally first** - Faster than Docker rebuilds
5. **Document in docker-compose.yml** - Add comments for clarity

## Example: Full docker-compose.yml

```yaml
services:
  # Generic collector - configured via environment
  dev-plans-collector:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - COLLECTOR_NAME=development_plans
      - CITY=boston  # Change city here
    volumes:
      - ./downloads:/app/downloads
    command: /app/scripts/run-collector.sh  # Same script for all

  # Generic parser - configured via environment
  dev-plans-parser:
    build:
      context: .
      dockerfile: Dockerfile
    depends_on:
      - ollama
    environment:
      - PARSER_NAME=development_plans
      - CITY=boston        # Change city here
      - MODEL=llama3.2     # Change model here
      - OLLAMA_HOST=http://ollama:11434
    volumes:
      - ./downloads:/app/downloads
    command: /app/scripts/run-parser-with-ollama.sh  # Same script for all
```

Simple, clean, and easy to manage!
