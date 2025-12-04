"""
FastAPI Server for AI FUN Token Wheel Generator

Provides REST API endpoints for session-based token generation and wheel visualization.
Uses a singleton GPT-2 generator instance shared across all sessions.

Educational purpose: Backend API for demonstrating how LLMs generate text by sampling
from probability distributions visualized as a spinning wheel.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager
import asyncio
import uuid
import os
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pathlib import Path

from generator import TokenWheelGenerator, SUPPORTED_MODELS

# Load environment variables from .env file
load_dotenv()


# ============================================================================
# Pydantic Models for Request/Response Validation
# ============================================================================

class SubTokenInfo(BaseModel):
    """Information about a sub-token in the 'other' category."""
    token: str = Field(..., description="The token string")
    token_id: int = Field(..., description="Token ID")
    probability: float = Field(..., ge=0.0, le=1.0, description="Token probability")


class WedgeInfo(BaseModel):
    """Information about a single token in the probability distribution."""
    token: str = Field(..., description="The token string (or '<OTHER>')")
    token_id: int = Field(..., description="Token ID (-1 for '<OTHER>')")
    probability: float = Field(..., ge=0.0, le=1.0, description="Token probability")
    is_special: bool = Field(..., description="Whether token is a special token")
    is_other: bool = Field(..., description="Whether this is the '<OTHER>' category")
    other_top_tokens: Optional[List[SubTokenInfo]] = Field(None, description="Top tokens from the 'other' category")
    remaining_count: Optional[int] = Field(None, description="Total count of remaining tokens")




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
    model: str = Field(..., description="Model key being used for this session")


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
    selected_token_probability: float = Field(..., description="The probability of the selected token")
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


class ModelInfo(BaseModel):
    """Information about a supported model."""
    key: str = Field(..., description="Model key (e.g., 'gpt2', 'llama-3.2-1b')")
    name: str = Field(..., description="Display name")
    params: str = Field(..., description="Parameter count (e.g., '124M')")
    size_mb: int = Field(..., description="Model size in MB")
    ram_required_gb: int = Field(..., description="RAM required in GB")
    available: bool = Field(..., description="Whether model is loaded and available")
    is_default: bool = Field(..., description="Whether this is the default model")
    requires_auth: bool = Field(..., description="Whether model requires HuggingFace token")


class ModelsResponse(BaseModel):
    """Response body for GET /api/models endpoint."""
    models: List[ModelInfo] = Field(..., description="List of supported models")
    default_model: str = Field(..., description="Key of the default model")


# ============================================================================
# Session Storage and Management
# ============================================================================

class SessionData:
    """Container for session state."""

    def __init__(
        self,
        session_id: str,
        current_context: str,
        model_key: str,
        min_threshold: float,
        secondary_threshold: float
    ):
        self.session_id = session_id
        self.current_context = current_context
        self.model_key = model_key  # Track which model this session uses
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
    - Load all available models into a registry (app.state.generators)
    - Track which models are available (app.state.available_models)
    - Set default model (app.state.default_model)
    - Start background task for session cleanup

    On shutdown:
    - Cancel background cleanup task
    - Clean up resources
    """
    # Startup: Load models into registry
    import time
    start_time = time.time()

    print("=" * 60)
    print("Starting AI FUN Token Wheel API...")
    print(f"Start time: {datetime.utcnow()}")
    print("=" * 60)

    # Get HuggingFace token from environment (only used for local dev, not Docker)
    # In Docker, models must be pre-loaded during build
    hf_token = os.environ.get('HF_TOKEN', None)
    if hf_token:
        print("HF_TOKEN found - will use for loading gated models (local dev mode)")
    else:
        print("No HF_TOKEN - will attempt to load models from cache (Docker mode)")

    # Initialize model registry
    app.state.generators = {}
    app.state.available_models = []

    # Load each supported model
    for model_key, config in SUPPORTED_MODELS.items():
        model_start = time.time()

        try:
            print(f"Loading {config['display_name']}...")

            # Always attempt to load (with token if available, from cache otherwise)
            # In Docker: models pre-loaded during build, no token needed
            # In local dev: token downloads models on first run
            generator = TokenWheelGenerator(model_key=model_key, hf_token=hf_token)
            app.state.generators[model_key] = generator
            app.state.available_models.append(model_key)

            model_end = time.time()
            print(f"✓ {config['display_name']} loaded in {model_end - model_start:.2f}s")

        except Exception as e:
            if config['requires_auth']:
                print(f"✗ Failed to load {config['display_name']} (not available - needs HF_TOKEN or pre-loaded cache)")
            else:
                print(f"✗ Failed to load {config['display_name']}: {e}")
            continue

    # Ensure at least one model loaded
    if not app.state.generators:
        raise RuntimeError("No models loaded! Cannot start server.")

    # Set default model (prefer configured default, fallback to first available)
    app.state.default_model = next(
        (k for k, c in SUPPORTED_MODELS.items()
         if c['is_default'] and k in app.state.available_models),
        app.state.available_models[0]
    )

    print("=" * 60)
    print(f"Server ready! Loaded {len(app.state.generators)} model(s):")
    for model_key in app.state.available_models:
        config = SUPPORTED_MODELS[model_key]
        default_marker = " [DEFAULT]" if model_key == app.state.default_model else ""
        print(f"  - {config['display_name']}{default_marker}")
    print(f"Total startup time: {time.time() - start_time:.2f} seconds")
    print(f"Ready time: {datetime.utcnow()}")
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

# Mount static files for serving the frontend
# Check if static directory exists (it will in production Docker container)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")


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


@app.get("/api/models", response_model=ModelsResponse)
async def get_models():
    """
    Get list of all supported models and their availability status.

    Returns:
        ModelsResponse with list of models and default model key

    Each model includes:
    - key: Model identifier
    - name: Display name
    - params: Parameter count
    - size_mb: Model size in MB
    - ram_required_gb: RAM required
    - available: Whether model is currently loaded
    - is_default: Whether this is the default model
    - requires_auth: Whether model requires HuggingFace token
    """
    models = [
        ModelInfo(
            key=model_key,
            name=config['display_name'],
            params=config['params'],
            size_mb=config['size_mb'],
            ram_required_gb=config['ram_required_gb'],
            available=(model_key in app.state.available_models),
            is_default=config['is_default'],
            requires_auth=config['requires_auth']
        )
        for model_key, config in SUPPORTED_MODELS.items()
    ]

    return ModelsResponse(
        models=models,
        default_model=app.state.default_model
    )


@app.post("/api/start", response_model=StartResponse)
async def start_generation(request: StartRequest):
    """
    Start a new text generation session.

    Creates a new session with a unique UUID, validates requested model,
    gets the initial token distribution, and returns tokens with probabilities.

    Args:
        request: StartRequest containing prompt and optional model/threshold parameters

    Returns:
        StartResponse with session_id, context, tokens, and model

    Raises:
        HTTPException: 400 if requested model unavailable, 500 if generation fails
    """
    try:
        # Validate and select model
        model_key = request.model if request.model else app.state.default_model

        # Check if requested model is available
        if model_key not in app.state.available_models:
            available = ", ".join(app.state.available_models)
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model_key}' is not available. Available models: {available}"
            )

        # Generate unique session ID
        session_id = str(uuid.uuid4())

        # Get the appropriate generator from registry
        generator = app.state.generators[model_key]

        # Get initial token distribution
        distribution = generator.get_next_token_distribution(
            context=request.prompt,
            min_threshold=request.min_threshold,
            secondary_threshold=request.secondary_threshold
        )

        # Get tokens with probabilities (no angles - frontend handles that)
        tokens = generator.get_tokens_with_probabilities(distribution)

        # Create session data with model binding
        session_data = SessionData(
            session_id=session_id,
            current_context=request.prompt,
            model_key=model_key,
            min_threshold=request.min_threshold,
            secondary_threshold=request.secondary_threshold
        )
        # Store current distribution for later token selection
        session_data.current_distribution = distribution

        # Store session
        sessions[session_id] = session_data

        # Convert tokens to Pydantic models
        token_models = [WedgeInfo(**token) for token in tokens]

        response = StartResponse(
            session_id=session_id,
            context=request.prompt,
            tokens=token_models,
            step=0,
            model=model_key
        )

        logging.info(f"Started session {session_id} with model {model_key}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error during generation: {e}", exc_info=True)
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
        # Get the generator for this session's model
        generator = app.state.generators[session.model_key]
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

        # Get the generator for this session's model
        generator = app.state.generators[session.model_key]
        selected_token_id = request.selected_token_id

        # Get the probability of the selected token
        if selected_token_id != -1:
            # For a specific token, find it in the current distribution
            selected_token = generator._decode_token(selected_token_id)

            # Look for the token in the distribution to get its probability
            token_probability = None
            for token in session.current_distribution['tokens']:
                if token['token_id'] == selected_token_id:
                    token_probability = token['probability']
                    break

            # If not found in main tokens, it must be from the "other" category
            # In this case, we need to get its probability from the full distribution
            if token_probability is None:
                import torch
                context = session.current_distribution['context']
                input_ids = generator.tokenizer.encode(context, return_tensors='pt').to(generator.device)
                with torch.no_grad():
                    outputs = generator.model(input_ids)
                    logits = outputs.logits[0, -1, :]
                    probabilities = torch.softmax(logits, dim=0)
                    token_probability = float(probabilities[selected_token_id].cpu().numpy())

            # Create token_info dict
            token_info = {
                'token_id': selected_token_id,
                'token': selected_token,
                'probability': token_probability
            }
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
                selected_token_probability=token_info['probability'],
                new_context=new_context,
                should_continue=True,
                next_tokens=next_token_models,
                step=session.step
            )
        else:
            # Generation complete
            return SelectResponse(
                selected_token=selected_token,
                selected_token_probability=token_info['probability'],
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


# ============================================================================
# Frontend Serving (Catch-all for SPA routing)
# ============================================================================

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """
    Serve the frontend React application.

    This catch-all route serves index.html for all non-API routes,
    enabling client-side routing for the React SPA.

    Only active when static directory exists (in production Docker container).
    """
    if static_dir.exists():
        # Serve index.html for all routes (SPA client-side routing)
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)

    # If static files don't exist, return 404
    raise HTTPException(status_code=404, detail="Frontend not found. Run in development mode or build Docker image.")
