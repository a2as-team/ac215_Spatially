"""Tests for the Chat API endpoints using SmartDataAgentRunner."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

# Test location: Fenway/Back Bay area in Boston (residential area)
TEST_LATITUDE = 42.351581
TEST_LONGITUDE = -71.082394
TEST_CITY = "boston"

# Test session ID to avoid polluting default session
TEST_SESSION_ID = "test-chat-api-session"


@pytest.mark.asyncio
class TestChatAPI:
    """Tests for Chat API endpoints."""

    async def test_get_chats_empty(self):
        """Test getting chats when none exist."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/chats/",
                headers={"X-Session-ID": "empty-session-unique-12345"}
            )
            assert response.status_code == 200
            assert response.json() == []

    async def test_start_chat_city_mode(self):
        """Test starting a new chat in city mode (no location)."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chats/",
                json={
                    "content": "What are the main zoning categories in Boston?",
                    "city": TEST_CITY,
                },
                headers={"X-Session-ID": TEST_SESSION_ID}
            )

            print("\n" + "=" * 60)
            print("START CHAT (city mode) RESPONSE:")
            print("=" * 60)

            assert response.status_code == 200
            data = response.json()

            print(f"Chat ID: {data.get('chat_id')}")
            print(f"Title: {data.get('title')}")
            print(f"Agent Type: {data.get('context', {}).get('agent_type')}")
            print(f"Messages: {len(data.get('messages', []))}")

            if data.get("messages"):
                for msg in data["messages"]:
                    role = msg.get("role")
                    content = msg.get("content", "")[:300]
                    print(f"\n[{role}]: {content}...")

            print("=" * 60 + "\n")

            assert "chat_id" in data
            assert "messages" in data
            assert len(data["messages"]) == 2
            assert data["context"]["agent_type"] == "city"

    async def test_start_chat_location_mode(self):
        """Test starting a new chat in location mode."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chats/",
                json={
                    "content": "What is the zoning at this location?",
                    "city": TEST_CITY,
                    "latitude": TEST_LATITUDE,
                    "longitude": TEST_LONGITUDE,
                },
                headers={"X-Session-ID": TEST_SESSION_ID}
            )

            print("\n" + "=" * 60)
            print(f"START CHAT (location mode) - ({TEST_LATITUDE}, {TEST_LONGITUDE})")
            print("=" * 60)

            assert response.status_code == 200
            data = response.json()

            print(f"Chat ID: {data.get('chat_id')}")
            print(f"Agent Type: {data.get('context', {}).get('agent_type')}")

            if data.get("messages"):
                for msg in data["messages"]:
                    role = msg.get("role")
                    content = msg.get("content", "")[:500]
                    print(f"\n[{role}]: {content}...")

            print("=" * 60 + "\n")

            assert data["context"]["agent_type"] == "location"
            assert data["context"]["latitude"] == TEST_LATITUDE
            assert data["context"]["longitude"] == TEST_LONGITUDE

    async def test_get_chat(self):
        """Test getting a specific chat."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # First create a chat
            create_response = await client.post(
                "/api/v1/chats/",
                json={
                    "content": "Tell me about residential zoning",
                    "city": TEST_CITY,
                },
                headers={"X-Session-ID": TEST_SESSION_ID}
            )
            chat_id = create_response.json()["chat_id"]

            # Now get it
            response = await client.get(
                f"/api/v1/chats/{chat_id}",
                headers={"X-Session-ID": TEST_SESSION_ID}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["chat_id"] == chat_id

    async def test_get_chat_not_found(self):
        """Test getting a non-existent chat."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/chats/non-existent-chat-id",
                headers={"X-Session-ID": TEST_SESSION_ID}
            )
            assert response.status_code == 404

    async def test_continue_chat(self):
        """Test continuing an existing chat with location."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # First create a chat with location
            create_response = await client.post(
                "/api/v1/chats/",
                json={
                    "content": "What is the zoning at this location?",
                    "city": TEST_CITY,
                    "latitude": TEST_LATITUDE,
                    "longitude": TEST_LONGITUDE,
                },
                headers={"X-Session-ID": TEST_SESSION_ID}
            )
            data = create_response.json()
            chat_id = data["chat_id"]

            print("\n" + "=" * 60)
            print(f"INITIAL CHAT (location: {TEST_LATITUDE}, {TEST_LONGITUDE}):")
            print("=" * 60)
            for msg in data["messages"]:
                print(f"\n[{msg['role'].upper()}]:")
                print(msg["content"])
            print("=" * 60)

            # Continue the chat
            continue_response = await client.post(
                f"/api/v1/chats/{chat_id}",
                json={"content": "What about height restrictions for this zone?"},
                headers={"X-Session-ID": TEST_SESSION_ID}
            )

            assert continue_response.status_code == 200
            data = continue_response.json()

            print("\n" + "=" * 60)
            print("FULL CHAT HISTORY AFTER CONTINUATION:")
            print("=" * 60)
            for i, msg in enumerate(data["messages"]):
                print(f"\n--- Message {i+1} [{msg['role'].upper()}] ---")
                print(msg["content"])
            print("\n" + "=" * 60)

            # Should now have 4 messages
            assert len(data["messages"]) == 4
            assert data["messages"][2]["role"] == "user"
            assert data["messages"][3]["role"] == "assistant"

    async def test_continue_chat_with_location_switch(self):
        """Test continuing a chat and switching to location mode."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Start in city mode
            create_response = await client.post(
                "/api/v1/chats/",
                json={
                    "content": "What are the zoning types in Boston?",
                    "city": TEST_CITY,
                },
                headers={"X-Session-ID": TEST_SESSION_ID}
            )
            chat_id = create_response.json()["chat_id"]

            print("\n" + "=" * 60)
            print("CITY MODE -> LOCATION MODE SWITCH:")
            print("=" * 60)

            # Continue with a location (switch to location mode)
            continue_response = await client.post(
                f"/api/v1/chats/{chat_id}",
                json={
                    "content": "What is the zoning at this specific location?",
                    "latitude": TEST_LATITUDE,
                    "longitude": TEST_LONGITUDE,
                },
                headers={"X-Session-ID": TEST_SESSION_ID}
            )

            assert continue_response.status_code == 200
            data = continue_response.json()

            print(f"Agent type after switch: {data['context']['agent_type']}")
            print(f"Location: ({data['context']['latitude']}, {data['context']['longitude']})")
            print(f"Response: {data['messages'][-1]['content'][:400]}...")
            print("=" * 60 + "\n")

            # Should now be in location mode
            assert data["context"]["agent_type"] == "location"
            assert data["context"]["latitude"] == TEST_LATITUDE

    async def test_delete_chat(self):
        """Test deleting a chat."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # First create a chat
            create_response = await client.post(
                "/api/v1/chats/",
                json={
                    "content": "Test chat to delete",
                    "city": TEST_CITY,
                },
                headers={"X-Session-ID": TEST_SESSION_ID}
            )
            chat_id = create_response.json()["chat_id"]

            # Delete it
            delete_response = await client.delete(
                f"/api/v1/chats/{chat_id}",
                headers={"X-Session-ID": TEST_SESSION_ID}
            )

            assert delete_response.status_code == 200
            assert delete_response.json()["status"] == "deleted"

            # Verify it's gone
            get_response = await client.get(
                f"/api/v1/chats/{chat_id}",
                headers={"X-Session-ID": TEST_SESSION_ID}
            )
            assert get_response.status_code == 404
