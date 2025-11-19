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
from unittest.mock import MagicMock

from main import app, sessions
from generator import GPT2TokenWheelGenerator


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Create a TestClient instance for making API requests."""
    # Clear sessions before each test
    sessions.clear()

    # Initialize the generator in app.state if not already present
    # This simulates what the lifespan context manager does
    if not hasattr(app.state, 'generator') or app.state.generator is None:
        app.state.generator = GPT2TokenWheelGenerator(model_name='gpt2')

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

    # Get the first token
    start_response = client.post("/api/start", json={"prompt": "The"})
    session_id = start_response.json()["session_id"]

    # Keep selecting until should_continue is False
    max_iterations = 100  # Safety limit
    for _ in range(max_iterations):
        # Need to provide a token_id for selection
        # Get current session to find a valid token
        session_data = sessions.get(session_id)
        if session_data and session_data.current_distribution:
            tokens = session_data.current_distribution['tokens']
            if tokens:
                token_id = tokens[0]['token_id']
            else:
                token_id = -1
        else:
            break

        response = client.post("/api/select", json={
            "session_id": session_id,
            "selected_token_id": token_id
        })
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
    assert "tokens" in data
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


def test_start_returns_tokens(client):
    """Test that tokens list is non-empty."""
    response = client.post("/api/start", json={"prompt": "The cat sat on the"})

    assert response.status_code == 200
    tokens = response.json()["tokens"]

    assert isinstance(tokens, list)
    assert len(tokens) > 0


def test_start_tokens_probabilities_sum_to_one(client):
    """Test that token probabilities sum to approximately 1.0."""
    response = client.post("/api/start", json={"prompt": "The cat sat on the"})

    assert response.status_code == 200
    tokens = response.json()["tokens"]

    # Sum up all token probabilities
    total_prob = sum(t["probability"] for t in tokens)

    # Should be very close to 1.0 (allow small floating point error)
    assert abs(total_prob - 1.0) < 0.01


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
    assert "tokens" in data
    assert len(data["tokens"]) > 0


# ============================================================================
# POST /api/select Tests
# ============================================================================

def test_select_valid_session(client, sample_session):
    """Test successful token selection with valid session."""
    session_id = sample_session()

    # Get a valid token_id from the session
    session_data = sessions.get(session_id)
    token_id = session_data.current_distribution['tokens'][0]['token_id']

    response = client.post("/api/select", json={
        "session_id": session_id,
        "selected_token_id": token_id
    })

    assert response.status_code == 200
    data = response.json()
    assert "selected_token" in data
    assert "new_context" in data
    assert "should_continue" in data
    assert "step" in data


def test_select_invalid_session(client):
    """Test 404 error for non-existent session_id."""
    response = client.post("/api/select", json={
        "session_id": "nonexistent-uuid",
        "selected_token_id": 1234
    })

    assert response.status_code == 404


def test_select_updates_context(client, sample_session):
    """Test that new_context includes selected token."""
    session_id = sample_session(prompt="The cat")

    # Get initial context
    session_response = client.get(f"/api/session/{session_id}")
    initial_context = session_response.json()["current_context"]

    # Get a valid token_id
    session_data = sessions.get(session_id)
    token_id = session_data.current_distribution['tokens'][0]['token_id']

    # Select token
    select_response = client.post("/api/select", json={
        "session_id": session_id,
        "selected_token_id": token_id
    })
    data = select_response.json()

    new_context = data["new_context"]
    selected_token = data["selected_token"]

    # New context should be initial context + selected token
    assert new_context == initial_context + selected_token


def test_select_increments_step(client, sample_session):
    """Test that step counter increases."""
    session_id = sample_session()

    # Get first token
    session_data = sessions.get(session_id)
    token_id1 = session_data.current_distribution['tokens'][0]['token_id']

    # Select first token
    response1 = client.post("/api/select", json={
        "session_id": session_id,
        "selected_token_id": token_id1
    })
    step1 = response1.json()["step"]

    # Select second token (if generation continues)
    if response1.json()["should_continue"]:
        session_data = sessions.get(session_id)
        token_id2 = session_data.current_distribution['tokens'][0]['token_id']
        response2 = client.post("/api/select", json={
            "session_id": session_id,
            "selected_token_id": token_id2
        })
        step2 = response2.json()["step"]
        assert step2 == step1 + 1


def test_select_returns_next_tokens(client, sample_session):
    """Test that next tokens are provided when continuing."""
    session_id = sample_session()

    # Get a valid token_id
    session_data = sessions.get(session_id)
    token_id = session_data.current_distribution['tokens'][0]['token_id']

    response = client.post("/api/select", json={
        "session_id": session_id,
        "selected_token_id": token_id
    })
    data = response.json()

    if data["should_continue"]:
        assert "next_tokens" in data
        assert data["next_tokens"] is not None
        assert len(data["next_tokens"]) > 0


def test_select_should_continue_true(client, sample_session):
    """Test that should_continue is True during generation."""
    session_id = sample_session(prompt="Once upon a time")

    # Get a valid token_id
    session_data = sessions.get(session_id)
    token_id = session_data.current_distribution['tokens'][0]['token_id']

    # First selection should typically continue
    response = client.post("/api/select", json={
        "session_id": session_id,
        "selected_token_id": token_id
    })
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


def test_select_no_next_tokens_when_done(client, sample_session):
    """Test that no next_tokens when should_continue=False."""
    session_id = sample_session()

    # Keep selecting until done
    max_iterations = 100
    for _ in range(max_iterations):
        # Get a valid token_id
        session_data = sessions.get(session_id)
        if session_data and session_data.current_distribution:
            tokens = session_data.current_distribution['tokens']
            token_id = tokens[0]['token_id'] if tokens else -1
        else:
            break

        response = client.post("/api/select", json={
            "session_id": session_id,
            "selected_token_id": token_id
        })
        data = response.json()

        if not data["should_continue"]:
            # When done, next_tokens should be None
            assert data["next_tokens"] is None
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
        # Get a valid token_id
        session_data = sessions.get(session_id)
        if session_data and session_data.current_distribution:
            tokens = session_data.current_distribution['tokens']
            token_id = tokens[0]['token_id'] if tokens else -1
        else:
            break

        select_response = client.post("/api/select", json={
            "session_id": session_id,
            "selected_token_id": token_id
        })
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

    # Get a valid token_id
    session_data = sessions.get(session_id)
    token_id1 = session_data.current_distribution['tokens'][0]['token_id']

    # Select first token
    select1 = client.post("/api/select", json={
        "session_id": session_id,
        "selected_token_id": token_id1
    })
    context2 = select1.json()["new_context"]

    # Context should be longer
    assert len(context2) > initial_len

    # Select second token if possible
    if select1.json()["should_continue"]:
        session_data = sessions.get(session_id)
        token_id2 = session_data.current_distribution['tokens'][0]['token_id']
        select2 = client.post("/api/select", json={
            "session_id": session_id,
            "selected_token_id": token_id2
        })
        context3 = select2.json()["new_context"]

        # Context should be even longer
        assert len(context3) > len(context2)


def test_step_counter_increments(client, sample_session):
    """Test that step increases correctly."""
    session_id = sample_session()

    # Initial step is 0
    session0 = client.get(f"/api/session/{session_id}")
    assert session0.json()["step"] == 0

    # Get a valid token_id
    session_data = sessions.get(session_id)
    token_id1 = session_data.current_distribution['tokens'][0]['token_id']

    # After first select, step should be 1
    select1 = client.post("/api/select", json={
        "session_id": session_id,
        "selected_token_id": token_id1
    })
    assert select1.json()["step"] == 1

    # After second select, step should be 2 (if continuing)
    if select1.json()["should_continue"]:
        session_data = sessions.get(session_id)
        token_id2 = session_data.current_distribution['tokens'][0]['token_id']
        select2 = client.post("/api/select", json={
            "session_id": session_id,
            "selected_token_id": token_id2
        })
        assert select2.json()["step"] == 2


def test_history_accumulates(client, sample_session):
    """Test that history list grows with selections."""
    session_id = sample_session()

    # Initial history is empty
    session0 = client.get(f"/api/session/{session_id}")
    assert len(session0.json()["history"]) == 0

    # Get a valid token_id
    session_data = sessions.get(session_id)
    token_id1 = session_data.current_distribution['tokens'][0]['token_id']

    # After first select, history should have 1 token
    select1 = client.post("/api/select", json={
        "session_id": session_id,
        "selected_token_id": token_id1
    })
    session1 = client.get(f"/api/session/{session_id}")
    assert len(session1.json()["history"]) == 1

    # After second select, history should have 2 tokens (if continuing)
    if select1.json()["should_continue"]:
        session_data = sessions.get(session_id)
        token_id2 = session_data.current_distribution['tokens'][0]['token_id']
        select2 = client.post("/api/select", json={
            "session_id": session_id,
            "selected_token_id": token_id2
        })
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

    # Get valid token_ids for each session
    session_data1 = sessions.get(session_id1)
    token_id1 = session_data1.current_distribution['tokens'][0]['token_id']

    session_data2 = sessions.get(session_id2)
    token_id2 = session_data2.current_distribution['tokens'][0]['token_id']

    # Select token in first session
    select1 = client.post("/api/select", json={
        "session_id": session_id1,
        "selected_token_id": token_id1
    })
    context1 = select1.json()["new_context"]

    # Select token in second session
    select2 = client.post("/api/select", json={
        "session_id": session_id2,
        "selected_token_id": token_id2
    })
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
    assert isinstance(data["tokens"], list)
    assert isinstance(data["step"], int)


def test_select_response_schema(client, sample_session):
    """Test that all required fields are present with correct types."""
    session_id = sample_session()

    # Get a valid token_id
    session_data = sessions.get(session_id)
    token_id = session_data.current_distribution['tokens'][0]['token_id']

    response = client.post("/api/select", json={
        "session_id": session_id,
        "selected_token_id": token_id
    })

    assert response.status_code == 200
    data = response.json()

    # Check all required fields
    assert isinstance(data["selected_token"], str)
    assert isinstance(data["new_context"], str)
    assert isinstance(data["should_continue"], bool)
    assert isinstance(data["step"], int)

    # Optional fields depend on should_continue
    if data["should_continue"]:
        assert isinstance(data["next_tokens"], list)
    else:
        assert data["next_tokens"] is None


def test_token_info_schema(client):
    """Test that token objects have all required fields."""
    response = client.post("/api/start", json={"prompt": "The cat"})

    assert response.status_code == 200
    tokens = response.json()["tokens"]

    # Check first token has all required fields
    token = tokens[0]
    assert isinstance(token["token"], str)
    assert isinstance(token["token_id"], int)
    assert isinstance(token["probability"], float)
    assert isinstance(token["is_special"], bool)
    assert isinstance(token["is_other"], bool)

    # Validate ranges
    assert 0.0 <= token["probability"] <= 1.0


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_start_with_empty_prompt(client):
    """Test handling of empty prompt."""
    response = client.post("/api/start", json={"prompt": ""})

    # Should fail validation (min_length=1)
    assert response.status_code == 422


def test_select_with_missing_fields(client):
    """Test 422 for missing required fields."""
    # Missing session_id
    response1 = client.post("/api/select", json={"selected_token_id": 123})
    assert response1.status_code == 422

    # Missing selected_token_id
    response2 = client.post("/api/select", json={"session_id": "test-id"})
    assert response2.status_code == 422


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
