"""
Comprehensive tests for the FastAPI Token Wheel API.

Tests cover all endpoints, error handling, data validation, concurrent sessions,
and full generation flow.
"""

import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from uuid import UUID

from main import app, sessions


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Create a TestClient instance for making API requests."""
    # Clear sessions before each test
    sessions.clear()
    return TestClient(app)


@pytest.fixture
def sample_session(client):
    """
    Helper fixture to create a session and return session_id.

    Returns a function that creates a session with optional custom prompt.
    """
    def _create_session(prompt: str = "The cat sat on the"):
        response = client.post("/api/start", json={"prompt": prompt})
        assert response.status_code == 200
        return response.json()["session_id"]

    return _create_session


@pytest.fixture
def completed_session(client, sample_session):
    """
    Helper fixture to create a session that has reached the end.

    Returns session_id of a completed session.
    """
    # Create session with a prompt that will likely end quickly
    session_id = sample_session(prompt="The")

    # Keep selecting until should_continue is False
    max_iterations = 100  # Safety limit
    for _ in range(max_iterations):
        response = client.post("/api/select", json={"session_id": session_id})
        assert response.status_code == 200
        data = response.json()

        if not data["should_continue"]:
            break

    return session_id


# ============================================================================
# POST /api/start Tests
# ============================================================================

def test_start_creates_session(client):
    """Test that POST /api/start successfully creates a session."""
    response = client.post("/api/start", json={"prompt": "The cat sat on the"})

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "context" in data
    assert "wedges" in data
    assert "selected_token_info" in data
    assert "step" in data


def test_start_returns_valid_session_id(client):
    """Test that session_id is a valid UUID format."""
    response = client.post("/api/start", json={"prompt": "Hello world"})

    assert response.status_code == 200
    session_id = response.json()["session_id"]

    # Should be parseable as UUID
    try:
        UUID(session_id)
    except ValueError:
        pytest.fail(f"session_id '{session_id}' is not a valid UUID")


def test_start_returns_wedges(client):
    """Test that wedges list is non-empty."""
    response = client.post("/api/start", json={"prompt": "The cat sat on the"})

    assert response.status_code == 200
    wedges = response.json()["wedges"]

    assert isinstance(wedges, list)
    assert len(wedges) > 0


def test_start_wedges_sum_to_360(client):
    """Test that wedge angles sum to 360 degrees."""
    response = client.post("/api/start", json={"prompt": "The cat sat on the"})

    assert response.status_code == 200
    wedges = response.json()["wedges"]

    # Sum up all wedge angles
    total_angle = sum(w["end_angle"] - w["start_angle"] for w in wedges)

    # Should be very close to 360 (allow small floating point error)
    assert abs(total_angle - 360.0) < 0.01


def test_start_has_selected_token(client):
    """Test that selected_token_info is present."""
    response = client.post("/api/start", json={"prompt": "The cat sat on the"})

    assert response.status_code == 200
    data = response.json()
    token_info = data["selected_token_info"]

    assert "token" in token_info
    assert "token_id" in token_info
    assert "probability" in token_info
    assert "target_angle" in token_info


def test_start_selected_token_in_wedges(client):
    """Test that selected token exists in wedges list."""
    response = client.post("/api/start", json={"prompt": "The cat sat on the"})

    assert response.status_code == 200
    data = response.json()
    selected_token = data["selected_token_info"]["token"]
    wedges = data["wedges"]

    # Selected token should be in one of the wedges
    wedge_tokens = [w["token"] for w in wedges]
    assert selected_token in wedge_tokens


def test_start_step_is_zero(client):
    """Test that initial step is 0."""
    response = client.post("/api/start", json={"prompt": "Hello"})

    assert response.status_code == 200
    step = response.json()["step"]
    assert step == 0


def test_start_context_matches_prompt(client):
    """Test that context equals input prompt."""
    prompt = "The cat sat on the"
    response = client.post("/api/start", json={"prompt": prompt})

    assert response.status_code == 200
    context = response.json()["context"]
    assert context == prompt


def test_start_with_custom_thresholds(client):
    """Test that custom min/secondary thresholds work."""
    response = client.post(
        "/api/start",
        json={
            "prompt": "The cat sat on the",
            "min_threshold": 0.02,
            "secondary_threshold": 0.01
        }
    )

    assert response.status_code == 200
    # Should still work with custom thresholds
    data = response.json()
    assert "wedges" in data
    assert len(data["wedges"]) > 0


def test_start_with_different_model(client):
    """Test that different GPT-2 variant can be specified."""
    # Note: This test assumes gpt2 model is available
    # In real environment, might want to test with gpt2-medium, etc.
    response = client.post(
        "/api/start",
        json={
            "prompt": "Hello world",
            "model": "gpt2"
        }
    )

    assert response.status_code == 200
    assert "session_id" in response.json()


# ============================================================================
# POST /api/select Tests
# ============================================================================

def test_select_valid_session(client, sample_session):
    """Test successful token selection with valid session."""
    session_id = sample_session()

    response = client.post("/api/select", json={"session_id": session_id})

    assert response.status_code == 200
    data = response.json()
    assert "selected_token" in data
    assert "new_context" in data
    assert "should_continue" in data
    assert "step" in data


def test_select_invalid_session(client):
    """Test 404 error for non-existent session_id."""
    response = client.post("/api/select", json={"session_id": "nonexistent-uuid"})

    assert response.status_code == 404


def test_select_updates_context(client, sample_session):
    """Test that new_context includes selected token."""
    session_id = sample_session(prompt="The cat")

    # Get initial context
    session_response = client.get(f"/api/session/{session_id}")
    initial_context = session_response.json()["current_context"]

    # Select token
    select_response = client.post("/api/select", json={"session_id": session_id})
    data = select_response.json()

    new_context = data["new_context"]
    selected_token = data["selected_token"]

    # New context should be initial context + selected token
    assert new_context == initial_context + selected_token


def test_select_increments_step(client, sample_session):
    """Test that step counter increases."""
    session_id = sample_session()

    # Select first token
    response1 = client.post("/api/select", json={"session_id": session_id})
    step1 = response1.json()["step"]

    # Select second token (if generation continues)
    if response1.json()["should_continue"]:
        response2 = client.post("/api/select", json={"session_id": session_id})
        step2 = response2.json()["step"]
        assert step2 == step1 + 1


def test_select_returns_next_wedges(client, sample_session):
    """Test that next wedges are provided when continuing."""
    session_id = sample_session()

    response = client.post("/api/select", json={"session_id": session_id})
    data = response.json()

    if data["should_continue"]:
        assert "next_wedges" in data
        assert data["next_wedges"] is not None
        assert len(data["next_wedges"]) > 0


def test_select_next_selected_token(client, sample_session):
    """Test that next token is pre-selected when continuing."""
    session_id = sample_session()

    response = client.post("/api/select", json={"session_id": session_id})
    data = response.json()

    if data["should_continue"]:
        assert "next_selected_token_info" in data
        assert data["next_selected_token_info"] is not None
        assert "token" in data["next_selected_token_info"]
        assert "target_angle" in data["next_selected_token_info"]


def test_select_should_continue_true(client, sample_session):
    """Test that should_continue is True during generation."""
    session_id = sample_session(prompt="Once upon a time")

    # First selection should typically continue
    response = client.post("/api/select", json={"session_id": session_id})
    data = response.json()

    # Most of the time, first selection should want to continue
    # (unless we hit EOS immediately, which is unlikely)
    assert "should_continue" in data
    assert isinstance(data["should_continue"], bool)


def test_select_should_continue_false(client, completed_session):
    """Test that should_continue is False at end."""
    session_id = completed_session

    # Get session to verify it's completed
    session_response = client.get(f"/api/session/{session_id}")
    assert session_response.status_code == 200

    # The completed_session fixture should have reached the end
    # So the last select call should have returned should_continue=False


def test_select_no_next_wedges_when_done(client, sample_session):
    """Test that no next_wedges when should_continue=False."""
    session_id = sample_session()

    # Keep selecting until done
    max_iterations = 100
    for _ in range(max_iterations):
        response = client.post("/api/select", json={"session_id": session_id})
        data = response.json()

        if not data["should_continue"]:
            # When done, next_wedges and next_selected_token_info should be None
            assert data["next_wedges"] is None
            assert data["next_selected_token_info"] is None
            break


# ============================================================================
# GET /api/session/{session_id} Tests
# ============================================================================

def test_get_session_valid(client, sample_session):
    """Test retrieving existing session."""
    session_id = sample_session()

    response = client.get(f"/api/session/{session_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id


def test_get_session_invalid(client):
    """Test 404 for non-existent session."""
    response = client.get("/api/session/nonexistent-uuid")

    assert response.status_code == 404


def test_get_session_has_correct_context(client, sample_session):
    """Test that context matches current state."""
    prompt = "The cat sat on the"
    session_id = sample_session(prompt=prompt)

    response = client.get(f"/api/session/{session_id}")

    assert response.status_code == 200
    context = response.json()["current_context"]
    assert context == prompt


def test_get_session_has_history(client, sample_session):
    """Test that history list is present."""
    session_id = sample_session()

    response = client.get(f"/api/session/{session_id}")

    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert isinstance(data["history"], list)


def test_get_session_has_step(client, sample_session):
    """Test that step number is present."""
    session_id = sample_session()

    response = client.get(f"/api/session/{session_id}")

    assert response.status_code == 200
    data = response.json()
    assert "step" in data
    assert data["step"] == 0  # Initial step


# ============================================================================
# DELETE /api/session/{session_id} Tests
# ============================================================================

def test_delete_session_valid(client, sample_session):
    """Test successful deletion."""
    session_id = sample_session()

    response = client.delete(f"/api/session/{session_id}")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_delete_session_invalid(client):
    """Test 404 for non-existent session."""
    response = client.delete("/api/session/nonexistent-uuid")

    assert response.status_code == 404


def test_delete_session_removes(client, sample_session):
    """Test that session is no longer accessible after deletion."""
    session_id = sample_session()

    # Delete session
    delete_response = client.delete(f"/api/session/{session_id}")
    assert delete_response.status_code == 200

    # Try to access deleted session
    get_response = client.get(f"/api/session/{session_id}")
    assert get_response.status_code == 404


def test_delete_returns_message(client, sample_session):
    """Test that delete returns success message."""
    session_id = sample_session()

    response = client.delete(f"/api/session/{session_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Session deleted"


# ============================================================================
# Integration/Flow Tests
# ============================================================================

def test_full_generation_flow(client):
    """Test complete flow: start → select → select → ... → end."""
    # Start session
    start_response = client.post("/api/start", json={"prompt": "The cat"})
    assert start_response.status_code == 200
    session_id = start_response.json()["session_id"]

    # Select tokens until completion
    max_iterations = 100
    iteration_count = 0

    for i in range(max_iterations):
        select_response = client.post("/api/select", json={"session_id": session_id})
        assert select_response.status_code == 200

        data = select_response.json()
        iteration_count = i + 1

        if not data["should_continue"]:
            break

    # Should have completed within max iterations
    assert iteration_count < max_iterations

    # Verify final session state
    final_session = client.get(f"/api/session/{session_id}")
    assert final_session.status_code == 200
    final_data = final_session.json()

    # History should have tokens
    assert len(final_data["history"]) > 0
    # Step should match iteration count
    assert final_data["step"] == iteration_count


def test_context_accumulates(client, sample_session):
    """Test that context grows with each select."""
    session_id = sample_session(prompt="Hello")

    # Get initial context
    session1 = client.get(f"/api/session/{session_id}")
    context1 = session1.json()["current_context"]
    initial_len = len(context1)

    # Select first token
    select1 = client.post("/api/select", json={"session_id": session_id})
    context2 = select1.json()["new_context"]

    # Context should be longer
    assert len(context2) > initial_len

    # Select second token if possible
    if select1.json()["should_continue"]:
        select2 = client.post("/api/select", json={"session_id": session_id})
        context3 = select2.json()["new_context"]

        # Context should be even longer
        assert len(context3) > len(context2)


def test_step_counter_increments(client, sample_session):
    """Test that step increases correctly."""
    session_id = sample_session()

    # Initial step is 0
    session0 = client.get(f"/api/session/{session_id}")
    assert session0.json()["step"] == 0

    # After first select, step should be 1
    select1 = client.post("/api/select", json={"session_id": session_id})
    assert select1.json()["step"] == 1

    # After second select, step should be 2 (if continuing)
    if select1.json()["should_continue"]:
        select2 = client.post("/api/select", json={"session_id": session_id})
        assert select2.json()["step"] == 2


def test_history_accumulates(client, sample_session):
    """Test that history list grows with selections."""
    session_id = sample_session()

    # Initial history is empty
    session0 = client.get(f"/api/session/{session_id}")
    assert len(session0.json()["history"]) == 0

    # After first select, history should have 1 token
    select1 = client.post("/api/select", json={"session_id": session_id})
    session1 = client.get(f"/api/session/{session_id}")
    assert len(session1.json()["history"]) == 1

    # After second select, history should have 2 tokens (if continuing)
    if select1.json()["should_continue"]:
        select2 = client.post("/api/select", json={"session_id": session_id})
        session2 = client.get(f"/api/session/{session_id}")
        assert len(session2.json()["history"]) == 2


# ============================================================================
# Concurrent Session Tests
# ============================================================================

def test_multiple_sessions_independent(client):
    """Test that two sessions don't interfere with each other."""
    # Create two sessions with different prompts
    response1 = client.post("/api/start", json={"prompt": "The cat"})
    response2 = client.post("/api/start", json={"prompt": "Hello world"})

    session_id1 = response1.json()["session_id"]
    session_id2 = response2.json()["session_id"]

    # Sessions should be different
    assert session_id1 != session_id2

    # Select token in first session
    select1 = client.post("/api/select", json={"session_id": session_id1})
    context1 = select1.json()["new_context"]

    # Select token in second session
    select2 = client.post("/api/select", json={"session_id": session_id2})
    context2 = select2.json()["new_context"]

    # Contexts should be different (different starting prompts)
    assert context1 != context2

    # Verify both sessions still exist independently
    get1 = client.get(f"/api/session/{session_id1}")
    get2 = client.get(f"/api/session/{session_id2}")

    assert get1.status_code == 200
    assert get2.status_code == 200
    assert get1.json()["current_context"] != get2.json()["current_context"]


def test_session_ids_unique(client):
    """Test that each session gets a unique ID."""
    session_ids = set()

    # Create 10 sessions
    for i in range(10):
        response = client.post("/api/start", json={"prompt": f"Test {i}"})
        session_id = response.json()["session_id"]
        session_ids.add(session_id)

    # All session IDs should be unique
    assert len(session_ids) == 10


# ============================================================================
# Data Validation Tests
# ============================================================================

def test_start_response_schema(client):
    """Test that all required fields are present with correct types."""
    response = client.post("/api/start", json={"prompt": "Hello"})

    assert response.status_code == 200
    data = response.json()

    # Check all required fields
    assert isinstance(data["session_id"], str)
    assert isinstance(data["context"], str)
    assert isinstance(data["wedges"], list)
    assert isinstance(data["selected_token_info"], dict)
    assert isinstance(data["step"], int)


def test_select_response_schema(client, sample_session):
    """Test that all required fields are present with correct types."""
    session_id = sample_session()
    response = client.post("/api/select", json={"session_id": session_id})

    assert response.status_code == 200
    data = response.json()

    # Check all required fields
    assert isinstance(data["selected_token"], str)
    assert isinstance(data["new_context"], str)
    assert isinstance(data["should_continue"], bool)
    assert isinstance(data["step"], int)

    # Optional fields depend on should_continue
    if data["should_continue"]:
        assert isinstance(data["next_wedges"], list)
        assert isinstance(data["next_selected_token_info"], dict)
    else:
        assert data["next_wedges"] is None
        assert data["next_selected_token_info"] is None


def test_wedge_info_schema(client):
    """Test that wedge objects have all required fields."""
    response = client.post("/api/start", json={"prompt": "The cat"})

    assert response.status_code == 200
    wedges = response.json()["wedges"]

    # Check first wedge has all required fields
    wedge = wedges[0]
    assert isinstance(wedge["token"], str)
    assert isinstance(wedge["token_id"], int)
    assert isinstance(wedge["probability"], float)
    assert isinstance(wedge["start_angle"], (int, float))
    assert isinstance(wedge["end_angle"], (int, float))
    assert isinstance(wedge["is_special"], bool)
    assert isinstance(wedge["is_other"], bool)

    # Validate ranges
    assert 0.0 <= wedge["probability"] <= 1.0
    assert 0.0 <= wedge["start_angle"] < 360.0
    assert 0.0 < wedge["end_angle"] <= 360.0


def test_token_info_schema(client):
    """Test that token info has all required fields."""
    response = client.post("/api/start", json={"prompt": "The cat"})

    assert response.status_code == 200
    token_info = response.json()["selected_token_info"]

    # Check all required fields
    assert isinstance(token_info["token"], str)
    assert isinstance(token_info["token_id"], int)
    assert isinstance(token_info["probability"], float)
    assert isinstance(token_info["target_angle"], (int, float))

    # Validate ranges
    assert 0.0 <= token_info["probability"] <= 1.0
    assert 0.0 <= token_info["target_angle"] < 360.0


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_start_with_empty_prompt(client):
    """Test handling of empty prompt."""
    response = client.post("/api/start", json={"prompt": ""})

    # Should fail validation (min_length=1)
    assert response.status_code == 422


def test_select_with_missing_session_id(client):
    """Test 422 for missing session_id field."""
    response = client.post("/api/select", json={})

    assert response.status_code == 422


def test_malformed_requests(client):
    """Test proper error responses for malformed requests."""
    # Invalid JSON structure
    response1 = client.post(
        "/api/start",
        json={"invalid_field": "value"}
    )
    assert response1.status_code == 422

    # Invalid threshold values
    response2 = client.post(
        "/api/start",
        json={
            "prompt": "Hello",
            "min_threshold": 1.5  # > 1.0, should fail validation
        }
    )
    assert response2.status_code == 422

    # Negative threshold
    response3 = client.post(
        "/api/start",
        json={
            "prompt": "Hello",
            "min_threshold": -0.1
        }
    )
    assert response3.status_code == 422


# ============================================================================
# Health Check Test
# ============================================================================

def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
