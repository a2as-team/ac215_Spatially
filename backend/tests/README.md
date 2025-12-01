# Backend Tests

## Running Tests with Docker Compose

### Run all tests
```bash
docker compose exec backend uv run pytest tests/ -v
```

### Run a specific test file
```bash
docker compose exec backend uv run pytest tests/test_agent_location.py -v -s
```

### Run a specific test class
```bash
docker compose exec backend uv run pytest tests/test_agent_location.py::TestLocationDataAgent -v -s
```

### Run a specific test method
```bash
docker compose exec backend uv run pytest tests/test_agent_location.py::TestSmartDataAgentRunner::test_init_location_mode -v -s
```

### Run with output (print statements visible)
```bash
docker compose exec backend uv run pytest tests/test_agent_location.py -v -s
```

### Run with a one-off container (if backend is not running)
```bash
docker compose run --rm backend uv run pytest tests/test_agent_location.py -v -s
```

## Test Files

| File | Description |
|------|-------------|
| `test_agent_location.py` | Tests for LocationDataAgent, CityDataAgent, and SmartDataAgentRunner |
| `test_chat_api.py` | Tests for Chat API endpoints (start_chat, get_chat, continue_chat, delete_chat) |

## Notes

- Async tests require `pytest-asyncio`. Add it with: `uv add pytest-asyncio --dev`
- Some tests (like `test_run_returns_response`) make actual API calls to Gemini and require valid credentials
- For CI, consider mocking external API calls
