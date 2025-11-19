"""
FastAPI Server for AI FUN Token Wheel Generator

Provides REST API endpoints for session-based token generation and wheel visualization.
Uses a singleton GPT-2 generator instance shared across all sessions.

Educational purpose: Backend API for demonstrating how LLMs generate text by sampling
from probability distributions visualized as a spinning wheel.
"""

from typing import Dict, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager
import asyncio
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from generator import GPT2TokenWheelGenerator


# ============================================================================
# Pydantic Models for Request/Response Validation
# ============================================================================

class WedgeInfo(BaseModel):
    """Information about a single token in the probability distribution."""
    token: str = Field(..., description="The token string (or '<OTHER>')")
    token_id: int = Field(..., description="Token ID (-1 for '<OTHER>')")
    probability: float = Field(..., ge=0.0, le=1.0, description="Token probability")
    is_special: bool = Field(..., description="Whether token is a special token")
    is_other: bool = Field(..., description="Whether this is the '<OTHER>' category")




class StartRequest(BaseModel):
    """Request body for POST /api/start endpoint."""
    prompt: str = Field(..., min_length=1, description="Initial prompt text")
    model: str = Field(default="gpt2", description="GPT-2 model variant")
    min_threshold: float = Field(default=0.1, ge=0.0, le=1.0, description="Primary probability threshold")
    secondary_threshold: float = Field(default=0.05, ge=0.0, le=1.0, description="Secondary probability threshold")


class StartResponse(BaseModel):
    """Response body for POST /api/start endpoint."""
    session_id: str = Field(..., description="Unique session identifier")
    context: str = Field(..., description="Current context (initially equals prompt)")
    tokens: List[WedgeInfo] = Field(..., description="List of tokens with probabilities")
    step: int = Field(..., description="Current step number (0 for initial)")


class SpinResponse(BaseModel):
    """Response for a spin request."""
    token: str = Field(..., description="The sampled token string")
    token_id: int = Field(..., description="The sampled token ID")
    probability: float = Field(..., description="The probability of the sampled token")
    target_angle: float = Field(..., description="The target angle on the wheel for animation")


class SessionIdRequest(BaseModel):
    session_id: str


class SelectRequest(BaseModel):
    """Request body for POST /api/select endpoint."""
    session_id: str = Field(..., description="Session identifier")
    selected_token_id: int = Field(..., description="Token ID of the selected token")



class SelectResponse(BaseModel):
    """Response body for POST /api/select endpoint."""
    selected_token: str = Field(..., description="The token that was selected")
    new_context: str = Field(..., description="Updated context with selected token appended")
    should_continue: bool = Field(..., description="Whether generation should continue")
    next_tokens: Optional[List[WedgeInfo]] = Field(None, description="Next tokens (if continuing)")
    step: int = Field(..., description="Current step number")


class SessionResponse(BaseModel):
    """Response body for GET /api/session/{session_id} endpoint."""
    session_id: str = Field(..., description="Session identifier")
    current_context: str = Field(..., description="Current context text")
    step: int = Field(..., description="Current step number")
    history: List[str] = Field(..., description="List of selected tokens")


class DeleteResponse(BaseModel):
    """Response body for DELETE /api/session/{session_id} endpoint."""
    message: str = Field(..., description="Success message")


class HealthResponse(BaseModel):
    """Response body for GET /api/health endpoint."""
    status: str = Field(..., description="Health status")


# ============================================================================
# Session Storage and Management
# ============================================================================

class SessionData:
    """Container for session state."""

    def __init__(
        self,
        session_id: str,
        current_context: str,
        min_threshold: float,
        secondary_threshold: float
    ):
        self.session_id = session_id
        self.current_context = current_context
        self.history: List[str] = []
        self.step = 0
        self.created_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.min_threshold = min_threshold
        self.secondary_threshold = secondary_threshold

        # Store the current distribution
        self.current_distribution: Optional[Dict] = None


# In-memory session storage
# Format: {session_id: SessionData}
sessions: Dict[str, SessionData] = {}

# Session configuration
SESSION_TTL_MINUTES = 30
CLEANUP_INTERVAL_MINUTES = 5


# ============================================================================
# Application Lifecycle Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup and shutdown.

    On startup:
    - Load GPT-2 model once and store in app.state
    - Start background task for session cleanup

    On shutdown:
    - Cancel background cleanup task
    - Clean up resources
    """
    # Startup: Load GPT-2 model once
    print("=" * 60)
    print("Starting AI FUN Token Wheel API...")
    print("=" * 60)

    generator = GPT2TokenWheelGenerator(model_name='gpt2')
    app.state.generator = generator

    print("=" * 60)
    print("Model loaded successfully! Server ready.")
    print("=" * 60)

    # Start background task for session cleanup
    cleanup_task = asyncio.create_task(cleanup_expired_sessions())

    try:
        yield
    finally:
        # Shutdown: Cancel cleanup task
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        print("Server shutting down...")


async def cleanup_expired_sessions():
    """
    Background task that runs every CLEANUP_INTERVAL_MINUTES to remove expired sessions.

    Sessions expire after SESSION_TTL_MINUTES of inactivity (based on last_accessed).
    """
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_MINUTES * 60)

        now = datetime.utcnow()
        expired_sessions = []

        for session_id, session_data in sessions.items():
            time_since_access = (now - session_data.last_accessed).total_seconds() / 60
            if time_since_access > SESSION_TTL_MINUTES:
                expired_sessions.append(session_id)

        # Remove expired sessions
        for session_id in expired_sessions:
            del sessions[session_id]
            print(f"Cleaned up expired session: {session_id}")

        if expired_sessions:
            print(f"Removed {len(expired_sessions)} expired session(s)")


# ============================================================================
# FastAPI Application Setup
# ============================================================================

app = FastAPI(
    title="AI FUN Token Wheel API",
    description="Backend API for visualizing LLM token generation as a probability wheel",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for verifying server status.

    Returns:
        HealthResponse with status "healthy"
    """
    return HealthResponse(status="healthy")


@app.post("/api/start", response_model=StartResponse)
async def start_generation(request: StartRequest):
    """
    Start a new text generation session.

    Creates a new session with a unique UUID, uses the shared GPT-2 generator,
    gets the initial token distribution, and returns tokens with probabilities.

    Args:
        request: StartRequest containing prompt and optional model/threshold parameters

    Returns:
        StartResponse with session_id, context, and tokens

    Raises:
        HTTPException: 500 if generation fails
    """
    try:
        # Generate unique session ID
        session_id = str(uuid.uuid4())

        # Use the shared generator from app.state
        generator = app.state.generator

        # Get initial token distribution
        distribution = generator.get_next_token_distribution(
            context=request.prompt,
            min_threshold=request.min_threshold,
            secondary_threshold=request.secondary_threshold
        )

        # Get tokens with probabilities (no angles - frontend handles that)
        tokens = generator.get_tokens_with_probabilities(distribution)

        # Create session data (no longer stores generator instance)
        session_data = SessionData(
            session_id=session_id,
            current_context=request.prompt,
            min_threshold=request.min_threshold,
            secondary_threshold=request.secondary_threshold
        )
        # Store current distribution for later token selection
        session_data.current_distribution = distribution

        # Store session
        sessions[session_id] = session_data

        # Convert tokens to Pydantic models
        token_models = [WedgeInfo(**token) for token in tokens]

        return StartResponse(
            session_id=session_id,
            context=request.prompt,
            tokens=token_models,
            step=0
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start generation: {str(e)}")


@app.post("/api/spin", response_model=SpinResponse)
async def spin_wheel(request: SessionIdRequest):
    """
    Probabilistically samples a token from the current distribution for a session.

    This endpoint performs the actual "spin" on the backend, selecting a token
    based on the probabilities. It returns the selected token and a target angle
    so the frontend can animate the wheel landing on the correct wedge.

    This does NOT advance the generation state. The frontend must still call
    /api/select with the returned token_id to confirm the choice.
    """
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session {request.session_id} not found")

    session = sessions[request.session_id]
    session.last_accessed = datetime.utcnow()  # Update last accessed time

    if session.current_distribution is None:
        raise HTTPException(status_code=500, detail="No current distribution in session")

    try:
        # Use the shared generator
        generator = app.state.generator
        sampled_token_info = generator.sample_token_from_distribution(
            session.current_distribution
        )

        return SpinResponse(
            token=sampled_token_info['token'],
            token_id=sampled_token_info['token_id'],
            probability=sampled_token_info['probability'],
            target_angle=sampled_token_info['target_angle']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sample token: {str(e)}")


@app.post("/api/select", response_model=SelectResponse)
async def select_token(request: SelectRequest):
    """
    Select a token by its ID and prepare for the next generation step.

    The frontend determines which token was selected (either by spin or manual click)
    and sends the token_id. The backend handles the selection and generates the next
    distribution.

    Args:
        request: SelectRequest containing session_id and selected_token_id

    Returns:
        SelectResponse with selected token, new context, continuation flag,
        and next tokens if continuing

    Raises:
        HTTPException: 404 if session not found, 400 if invalid request, 500 if generation fails
    """
    # Retrieve session
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session {request.session_id} not found")

    session = sessions[request.session_id]
    session.last_accessed = datetime.utcnow()  # Update last accessed time

    try:
        # Check if we have current distribution
        if session.current_distribution is None:
            raise HTTPException(status_code=400, detail="No current distribution in session")

        # Use the shared generator
        generator = app.state.generator
        selected_token_id = request.selected_token_id

        # If the frontend provides a specific token ID (from a spin, or a click on a specific wedge),
        # we can just decode it. This avoids an error if the token was sampled from the "other" group.
        if selected_token_id != -1:
            selected_token = generator.tokenizer.decode([selected_token_id])
            # Create a minimal token_info dict for should_end_generation
            token_info = {'token_id': selected_token_id, 'token': selected_token}
        else:
            # If token_id is -1, user clicked the generic "Other" wedge manually.
            # Here, we must sample a token from that group. select_token_by_id handles this.
            token_info = generator.select_token_by_id(
                session.current_distribution,
                -1
            )
            selected_token = token_info['token']

        # Append token to context
        new_context = session.current_context + selected_token
        session.current_context = new_context

        # Add to history
        session.history.append(selected_token)

        # Increment step
        session.step += 1

        # Check if we should end generation
        should_continue = not generator.should_end_generation(
            token_info=token_info,
            context=new_context
        )

        if should_continue:
            # Get next token distribution
            next_distribution = generator.get_next_token_distribution(
                context=new_context,
                min_threshold=session.min_threshold,
                secondary_threshold=session.secondary_threshold
            )

            # Get tokens with probabilities
            next_tokens = generator.get_tokens_with_probabilities(next_distribution)

            # Store distribution for next iteration
            session.current_distribution = next_distribution

            # Convert to Pydantic models
            next_token_models = [WedgeInfo(**token) for token in next_tokens]

            return SelectResponse(
                selected_token=selected_token,
                new_context=new_context,
                should_continue=True,
                next_tokens=next_token_models,
                step=session.step
            )
        else:
            # Generation complete
            return SelectResponse(
                selected_token=selected_token,
                new_context=new_context,
                should_continue=False,
                next_tokens=None,
                step=session.step
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to select token: {str(e)}")


@app.get("/api/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    Retrieve current session state.

    Args:
        session_id: Session identifier from path parameter

    Returns:
        SessionResponse with session_id, current_context, step, and history

    Raises:
        HTTPException: 404 if session not found
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    session = sessions[session_id]
    session.last_accessed = datetime.utcnow()  # Update last accessed time

    return SessionResponse(
        session_id=session.session_id,
        current_context=session.current_context,
        step=session.step,
        history=session.history
    )


@app.delete("/api/session/{session_id}", response_model=DeleteResponse)
async def delete_session(session_id: str):
    """
    Delete a session and free its resources.

    Args:
        session_id: Session identifier from path parameter

    Returns:
        DeleteResponse with success message

    Raises:
        HTTPException: 404 if session not found
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Remove session from storage
    del sessions[session_id]

    return DeleteResponse(message="Session deleted")
