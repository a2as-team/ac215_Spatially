"""Tests for LocationDataAgent and SmartDataAgentRunner."""

import pytest
from app.agents import (
    SmartDataAgentRunner,
    LocationDataAgent,
    CityDataAgent,
)

# Test location: Fenway/Back Bay area in Boston (residential area)
# https://www.google.com/maps/place/42%C2%B021'05.7%22N+71%C2%B004'56.6%22W
TEST_LATITUDE = 42.351581
TEST_LONGITUDE = -71.082394
TEST_CITY = "boston"


class TestLocationDataAgent:
    """Tests for LocationDataAgent."""

    def test_init(self):
        """Test agent initialization."""
        agent = LocationDataAgent(
            latitude=TEST_LATITUDE,
            longitude=TEST_LONGITUDE,
            city=TEST_CITY,
        )
        assert agent.latitude == TEST_LATITUDE
        assert agent.longitude == TEST_LONGITUDE
        assert agent.city == TEST_CITY

    def test_create_returns_llm_agent(self):
        """Test that create() returns an LlmAgent."""
        agent = LocationDataAgent(
            latitude=TEST_LATITUDE,
            longitude=TEST_LONGITUDE,
            city=TEST_CITY,
        )
        llm_agent = agent.create()
        assert llm_agent is not None
        assert llm_agent.name == "LocationDataAgent"

    def test_get_context(self):
        """Test get_context returns correct data."""
        agent = LocationDataAgent(
            latitude=TEST_LATITUDE,
            longitude=TEST_LONGITUDE,
            city=TEST_CITY,
        )
        context = agent.get_context()
        assert context["agent_type"] == "location"
        assert context["latitude"] == TEST_LATITUDE
        assert context["longitude"] == TEST_LONGITUDE
        assert context["city"] == TEST_CITY


class TestCityDataAgent:
    """Tests for CityDataAgent."""

    def test_init(self):
        """Test agent initialization."""
        agent = CityDataAgent(city=TEST_CITY)
        assert agent.city == TEST_CITY

    def test_create_returns_llm_agent(self):
        """Test that create() returns an LlmAgent."""
        agent = CityDataAgent(city=TEST_CITY)
        llm_agent = agent.create()
        assert llm_agent is not None
        assert llm_agent.name == "CityDataAgent"

    def test_get_context(self):
        """Test get_context returns correct data."""
        agent = CityDataAgent(city=TEST_CITY)
        context = agent.get_context()
        assert context["agent_type"] == "city"
        assert context["city"] == TEST_CITY


class TestSmartDataAgentRunner:
    """Tests for SmartDataAgentRunner."""

    def test_init_location_mode(self):
        """Test runner initialization in location mode."""
        runner = SmartDataAgentRunner(
            city=TEST_CITY,
            latitude=TEST_LATITUDE,
            longitude=TEST_LONGITUDE,
        )
        assert runner.city == TEST_CITY
        assert runner.latitude == TEST_LATITUDE
        assert runner.longitude == TEST_LONGITUDE
        assert runner.agent_type == "location"
        assert runner.is_location_based() is True

    def test_init_city_mode(self):
        """Test runner initialization in city mode."""
        runner = SmartDataAgentRunner(city=TEST_CITY)
        assert runner.city == TEST_CITY
        assert runner.latitude is None
        assert runner.longitude is None
        assert runner.agent_type == "city"
        assert runner.is_location_based() is False

    def test_get_context(self):
        """Test get_context returns all required fields."""
        runner = SmartDataAgentRunner(
            city=TEST_CITY,
            latitude=TEST_LATITUDE,
            longitude=TEST_LONGITUDE,
        )
        context = runner.get_context()
        assert "city" in context
        assert "latitude" in context
        assert "longitude" in context
        assert "agent_type" in context
        assert "session_id" in context
        assert "user_id" in context
        assert "chat_id" in context
        assert "history" in context

    def test_history_management(self):
        """Test history get/set/clear."""
        runner = SmartDataAgentRunner(city=TEST_CITY)

        # Initially empty
        assert runner.get_history() == []

        # Set history
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        runner.set_history(history)
        restored = runner.get_history()
        assert len(restored) == 2
        assert restored[0]["role"] == "user"
        assert restored[0]["content"] == "Hello"

        # Clear history
        runner.clear_history()
        assert runner.get_history() == []


@pytest.mark.asyncio
class TestSmartDataAgentRunnerAsync:
    """Async tests for SmartDataAgentRunner."""

    async def test_switch_to_city_mode(self):
        """Test switching from location to city mode."""
        runner = SmartDataAgentRunner(
            city=TEST_CITY,
            latitude=TEST_LATITUDE,
            longitude=TEST_LONGITUDE,
        )
        assert runner.is_location_based() is True

        await runner.switch_to_city_mode()

        assert runner.is_location_based() is False
        assert runner.latitude is None
        assert runner.longitude is None

    async def test_switch_to_location_mode(self):
        """Test switching from city to location mode."""
        runner = SmartDataAgentRunner(city=TEST_CITY)
        assert runner.is_location_based() is False

        await runner.switch_to_location_mode(
            latitude=TEST_LATITUDE,
            longitude=TEST_LONGITUDE,
        )

        assert runner.is_location_based() is True
        assert runner.latitude == TEST_LATITUDE
        assert runner.longitude == TEST_LONGITUDE

    async def test_run_returns_response(self):
        """Test that run() returns a response string."""
        runner = SmartDataAgentRunner(
            city=TEST_CITY,
            latitude=TEST_LATITUDE,
            longitude=TEST_LONGITUDE,
        )

        question = "What is the zoning at this location?"
        response = await runner.run(question)

        print("\n" + "=" * 60)
        print(f"Location: ({TEST_LATITUDE}, {TEST_LONGITUDE}) - Fenway/Back Bay")
        print(f"QUESTION: {question}")
        print("=" * 60)
        print("RESPONSE:")
        print(response)
        print("=" * 60 + "\n")

        assert isinstance(response, str)
        assert len(response) > 0
        # Check history was updated
        history = runner.get_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    async def test_from_context(self):
        """Test creating runner from saved context."""
        # Create original runner
        original = SmartDataAgentRunner(
            city=TEST_CITY,
            latitude=TEST_LATITUDE,
            longitude=TEST_LONGITUDE,
        )
        original.set_history([
            {"role": "user", "content": "Test question"},
            {"role": "assistant", "content": "Test answer"},
        ])

        # Get context and restore
        context = original.get_context()
        restored = await SmartDataAgentRunner.from_context(context)

        assert restored.city == original.city
        assert restored.latitude == original.latitude
        assert restored.longitude == original.longitude
        assert restored.agent_type == original.agent_type

    async def test_context_switch_location_to_city(self):
        """Test switching from location mode to city mode preserves context."""
        runner = SmartDataAgentRunner(
            city=TEST_CITY,
            latitude=TEST_LATITUDE,
            longitude=TEST_LONGITUDE,
        )

        # Ask a location-specific question
        question1 = "What can I build at this location? Is it residential?"
        response1 = await runner.run(question1)
        print("\n" + "=" * 60)
        print(f"Location: ({TEST_LATITUDE}, {TEST_LONGITUDE}) - Fenway/Back Bay")
        print(f"QUESTION (location mode): {question1}")
        print("=" * 60)
        print("RESPONSE:")
        print(response1)
        print("=" * 60)

        assert runner.is_location_based() is True
        assert len(runner.get_history()) == 2

        # Switch to city mode
        await runner.switch_to_city_mode()

        assert runner.is_location_based() is False
        # History should still be preserved
        assert len(runner.get_history()) == 2

        # Ask a follow-up question - agent should have context from previous conversation
        question2 = "What about residential zones in the city?"
        response2 = await runner.run(question2)
        print("\n" + "=" * 60)
        print(f"QUESTION (city mode after switch): {question2}")
        print("=" * 60)
        print("RESPONSE:")
        print(response2)
        print("=" * 60 + "\n")

        assert isinstance(response2, str)
        assert len(response2) > 0
        assert len(runner.get_history()) == 4

    async def test_context_switch_city_to_location(self):
        """Test switching from city mode to location mode preserves context."""
        runner = SmartDataAgentRunner(city=TEST_CITY)

        # Ask a city-wide question
        question1 = "What are the main zoning categories in Boston?"
        response1 = await runner.run(question1)
        print("\n" + "=" * 60)
        print(f"QUESTION (city mode): {question1}")
        print("=" * 60)
        print("RESPONSE:")
        print(response1)
        print("=" * 60)

        assert runner.is_location_based() is False

        # Switch to location mode
        await runner.switch_to_location_mode(latitude=TEST_LATITUDE, longitude=TEST_LONGITUDE)

        assert runner.is_location_based() is True

        # Ask a location-specific follow-up
        question2 = "What zone is this specific location in?"
        response2 = await runner.run(question2)
        print("\n" + "=" * 60)
        print(f"Location: ({TEST_LATITUDE}, {TEST_LONGITUDE}) - Fenway/Back Bay")
        print(f"QUESTION (location mode after switch): {question2}")
        print("=" * 60)
        print("RESPONSE:")
        print(response2)
        print("=" * 60 + "\n")

        assert isinstance(response2, str)
        assert len(response2) > 0

    async def test_census_query(self):
        """Test querying census data through the agent."""
        runner = SmartDataAgentRunner(city=TEST_CITY)

        question = "What is the total population of Boston?"
        response = await runner.run(question)

        print("\n" + "=" * 60)
        print(f"QUESTION (census): {question}")
        print("=" * 60)
        print("RESPONSE:")
        print(response)
        print("=" * 60 + "\n")

        assert isinstance(response, str)
        assert len(response) > 0

    async def test_census_query_with_location(self):
        """Test querying census data with a specific location."""
        runner = SmartDataAgentRunner(
            city=TEST_CITY,
            latitude=TEST_LATITUDE,
            longitude=TEST_LONGITUDE,
        )

        question = "What is the median household income in Boston?"
        response = await runner.run(question)

        print("\n" + "=" * 60)
        print(f"Location: ({TEST_LATITUDE}, {TEST_LONGITUDE}) - Fenway/Back Bay")
        print(f"QUESTION (census with location): {question}")
        print("=" * 60)
        print("RESPONSE:")
        print(response)
        print("=" * 60 + "\n")

        assert isinstance(response, str)
        assert len(response) > 0

    async def test_residential_zoning_query(self):
        """Test querying about residential zoning at a known residential location."""
        runner = SmartDataAgentRunner(
            city=TEST_CITY,
            latitude=TEST_LATITUDE,
            longitude=TEST_LONGITUDE,
        )

        question = "Is this location zoned for residential use? What types of housing are allowed here?"
        response = await runner.run(question)

        print("\n" + "=" * 60)
        print(f"Location: ({TEST_LATITUDE}, {TEST_LONGITUDE}) - Fenway/Back Bay (residential area)")
        print(f"QUESTION: {question}")
        print("=" * 60)
        print("RESPONSE:")
        print(response)
        print("=" * 60 + "\n")

        assert isinstance(response, str)
        assert len(response) > 0
