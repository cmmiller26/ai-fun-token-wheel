# Architecture Documentation

## System Overview

AI FUN Token Wheel is a client-server application that visualizes LLM token generation through a probability wheel interface. The application currently supports two language models: GPT-2 (124M) as the default, and TinyLlama 1.1B as a modern alternative. Both models run locally via Hugging Face Transformers with no API costs and no authentication required.

The architecture consists of two main components:

1. **Backend (Python/FastAPI)**: Handles model inference for the selected model, probability calculations, and token sampling
2. **Frontend (React/Vite)**: Renders spinning wheel visualization and manages user interaction

The probability extraction and token selection mechanism works identically for both models - and any future autoregressive LLM.

## Supported Models

The application supports multiple language models through Hugging Face Transformers. All models run locally with no API costs. Both supported models are pre-loaded in the Docker image for instant availability.

### Current Models

| Model                | Parameters | RAM Required | Download Size | Pre-loaded | Default | Notes                               |
| -------------------- | ---------- | ------------ | ------------- | ---------- | ------- | ----------------------------------- |
| **GPT-2**            | 124M       | 2 GB         | ~500 MB       | ✓ Yes      | ✓ Yes   | Most accessible, proven reliable    |
| **TinyLlama 1.1B** | 1.1B       | 4 GB         | ~2.2 GB       | ✓ Yes      | No      | Modern architecture, better quality |

### Model Selection

- **Default**: GPT-2 (124M) - Chosen for accessibility and reliability
- **Alternative**: TinyLlama 1.1B - For users with sufficient RAM (4GB+) who want to explore a more modern model
- **Comparison**: Students can switch between models to see how different LLMs produce different probability distributions for the same context

### Resource Requirements

**Minimum system requirements:**

- To run GPT-2: 4GB RAM total (2GB for model + 2GB for system)
- To run TinyLlama 1.1B: 6GB RAM total (4GB for model + 2GB for system)
- Docker image size: ~3-4 GB (includes both models pre-loaded)
- Disk space: 5GB free space recommended

### Extensibility

The architecture supports ANY autoregressive language model available through Hugging Face Transformers. Future models can be added by:

1. Adding model configuration to `SUPPORTED_MODELS` dict
2. (Optional) Pre-loading in Dockerfile for instant availability
3. No changes to core token generation logic required

Potential future additions: GPT-2 Medium/Large, Llama 3.2 models, GPT-Neo, Mistral variants, or other Hugging Face models as they become available.

## High-Level Data Flow

```text
User Input → Backend (Probabilities) → Frontend (Wedge Calculations) →
Wheel Rendering → User Spins/Selects → Frontend Determines Token ID →
Backend Processes Selection → Display Selected Token → Update Context → Repeat
```

### Detailed Flow

1. **Initial Request**: User provides starting prompt (e.g., "The cat sat on the")
2. **Probability Extraction**: Backend feeds prompt to GPT-2, extracts logits for next token
3. **Dynamic Token Selection**: Backend identifies top tokens using threshold-based approach (≥1% probability)
4. **Token List Response**: Backend returns list of tokens with probabilities (no angles)
5. **Frontend Wedge Calculation**: Frontend calculates wedge angles from probabilities
6. **Wheel Rendering**: Wheel rendered with wedges sized by probability, labeled with tokens
7. **User Selection**: User either spins the wheel (random angle) OR manually clicks a wedge
8. **Token Determination**:
   - If spin: Frontend generates random rotation → Calculates which wedge is under pointer → Gets token_id
   - If manual: Frontend gets token_id directly from clicked wedge
9. **Backend Processing**: Frontend sends selected_token_id to backend
10. **Display Result**: Backend returns selected token, which is shown and appended to context
11. **Context Update**: New context generates new probability distribution
12. **Iteration**: Process repeats with new context until stopping condition

## Backend Architecture

### Technology Stack

- **Python 3.10+** (3.11 for better performance)
- **FastAPI**: Async web framework for API endpoints
- **PyTorch**: Deep learning framework (required by Transformers)
- **Hugging Face Transformers**: Unified interface for all supported models
  - Currently supports: GPT-2 (124M, default) and TinyLlama 1.1B (1.1B)
  - Model-agnostic architecture: Easy to add future models
- **Uvicorn**: ASGI server

### Core Components

#### 1. TokenWheelGenerator Class

**File**: `backend/generator.py`

The main class handling all model inference, probability calculations, and token sampling. Model-agnostic design works with any Hugging Face causal language model.

**Key Methods**:

```python
__init__(model_name='gpt2', device='cpu', hf_token=None)
# Loads specified model and tokenizer from Hugging Face
# Args:
#   model_name: Key from SUPPORTED_MODELS ('gpt2' or 'tinyllama-1.1b')
#   device: 'cpu' or 'cuda' (CPU-only for most educational deployments)
#   hf_token: Optional Hugging Face token (not needed for current models)
# Uses AutoModelForCausalLM and AutoTokenizer for model-agnostic loading
# Handles model-specific initialization (e.g., pad tokens for Llama)
# Both supported models are pre-loaded in Docker, so loading is instant

get_next_token_distribution(context, min_threshold=0.01, secondary_threshold=0.005)
# Input: Text context, primary threshold (default 1%), secondary threshold (default 0.5%)
# Output: Dynamic set of tokens with probabilities
# Process:
#   1. Tokenize context
#   2. Forward pass through selected model (GPT-2 or TinyLlama 1.1B)
#   3. Apply softmax to logits
#   4. Select tokens ≥ min_threshold (1%)
#   5. If remaining probability > 20%, also include tokens ≥ secondary_threshold
#   6. Calculate remaining probability for "other" category
# Returns: List of {token, token_id, probability} + remaining_probability
# Note: Typically returns 10-30 tokens depending on distribution shape

get_tokens_with_probabilities(distribution)
# Input: Token distribution from get_next_token_distribution()
# Output: List of tokens with probabilities (no angles)
# Process:
#   1. For each token, create dict with token, token_id, probability, is_special, is_other
#   2. Add "other" category if remaining_probability > 0
# Returns: Simple list for frontend to handle wedge angle calculations
# Note: Backend no longer calculates angles - this is frontend responsibility

select_token_by_id(distribution, token_id)
# Input: Token distribution, token ID to select
# Output: Selected token info
# Process:
#   1. Find token with matching token_id
#   2. If token_id == -1 (other), sample from remaining distribution
#   3. Return token details
# Note: This is the only token selection method - frontend always sends token_id

_sample_from_other(distribution, other_wedge, target_angle)
# Input: Token distribution, other wedge info, target angle
# Output: Token sampled from remaining distribution
# Process:
#   1. Re-run model inference to get full probability distribution
#   2. Filter out tokens already in main distribution
#   3. Sample from remaining tokens based on their probabilities
#   4. Return selected token from "other" category
# Note: When "other" is selected, returns actual token (not literal "<OTHER>")

should_end_generation(token_info, context, max_length=50)
# Input: Token information, current context, max length
# Output: Boolean - should generation stop?
# Process: Check if EOS token, max length, or other stopping conditions
```

**Model-Agnostic Design**: This class works identically regardless of which model is loaded. The probability extraction logic (`get_next_token_distribution`), token selection (`select_token_by_id`), and all other methods operate the same way for GPT-2, TinyLlama 1.1B, or any future model. The educational visualization (probability wheel with wedge sizes) remains accurate and consistent across all models.

**Why This Works**: All autoregressive language models follow the same fundamental pattern:

1. Take context tokens as input
2. Generate logits (raw scores) for all possible next tokens
3. Apply softmax to convert to probabilities
4. Sample from this distribution

Our implementation uses this universal pattern, making it work with any Hugging Face causal LM.

#### 2. FastAPI Server

**File**: `backend/main.py`

REST API wrapping the TokenWheelGenerator.

**Endpoints**:

```http
GET /api/models
    Response: {
        "models": [
            {
                "key": "gpt2",
                "name": "GPT-2 (124M)",
                "params": "124M",
                "size_mb": 500,
                "ram_required_gb": 2,
                "preloaded": true,
                "is_default": true,
                "requires_auth": false
            },
            {
                "key": "tinyllama-1.1b",
                "name": "TinyLlama 1.1B",
                "params": "1.1B",
                "size_mb": 2200,
                "ram_required_gb": 4,
                "preloaded": true,
                "is_default": false,
                "requires_auth": false
            }
        ],
        "default_model": "gpt2"
    }

POST /api/start
    Body: {
        "prompt": "The cat sat on the",
        "model": "gpt2",                    // optional, default "gpt2"
                                            // options: "gpt2", "tinyllama-1.1b"
        "min_threshold": 0.01,              // optional, default 0.01 (1%)
        "secondary_threshold": 0.005        // optional, default 0.005 (0.5%)
    }
    Response: {
        "session_id": "abc123",
        "model": "gpt2",                    // Which model is being used
        "context": "The cat sat on the",
        "tokens": [                         // List of tokens with probabilities (no angles)
            {
                "token": " floor",
                "token_id": 1234,
                "probability": 0.076,
                "is_special": false,
                "is_other": false
            },
            {
                "token": " bed",
                "token_id": 5678,
                "probability": 0.065,
                "is_special": false,
                "is_other": false
            },
            ...
            {
                "token": "<OTHER>",
                "token_id": -1,
                "probability": 0.573,
                "is_special": false,
                "is_other": true
            }
        ],
        "step": 0
    }

POST /api/select
    Body: {
        "session_id": "abc123",
        "selected_token_id": 1234           // Token ID selected by user (from spin or manual click)
    }
    Response: {
        "selected_token": " floor",         // Actual token text (not "<OTHER>" if other was selected)
        "new_context": "The cat sat on the floor",
        "should_continue": true,
        "next_tokens": [...],               // Next token list (if continuing)
        "step": 1
    }

GET /api/session/{session_id}
    Response: {
        "session_id": "abc123",
        "current_context": "The cat sat on the floor",
        "step": 1,
        "history": [...]
    }

DELETE /api/session/{session_id}
    Response: {
        "message": "Session deleted"
    }
```

### Key Algorithms

#### Token Selection with "Other" Handling

**Goal**: Select a token by ID, properly handling the "other" category

**Algorithm (Backend)**:

```python
1. Receive token_id from frontend

2. If token_id is in the main distribution:
   - Return that token directly

3. If token_id == -1 (other category):
   - Re-run model inference to get full probability distribution
   - Filter out tokens already in main distribution
   - Sample from remaining tokens based on their probabilities
   - Return the sampled token (actual token, not "<OTHER>")

4. Append selected token to context
5. Generate next distribution for next step
```

**Example** (when "other" is selected):

```text
Main distribution has 8 tokens (32.6% total probability)
Remaining distribution has 50,249 tokens (67.4% total probability)

When user selects "other":
  1. Sample from the 50,249 remaining tokens
  2. Weighted by their probabilities (normalized to sum to 1.0)
  3. Might select: " table", " shelf", " windowsill", etc.
  4. Return the actual sampled token
```

#### Wedge Angle Calculation (Frontend)

**Goal**: Calculate wedge angles from token probabilities

**Algorithm (Frontend - JavaScript)**:

```javascript
1. Receive token list with probabilities from backend

2. Calculate wedge angles sequentially:
   - Start at angle 0°
   - For each token:
     * wedge_angle = (token_probability / 1.0) × 360°
     * start_angle = current_angle
     * end_angle = current_angle + wedge_angle
     * current_angle = end_angle
     * Add {start_angle, end_angle} to token object

3. Return tokens with angle data for rendering
```

**Example** (context = "The cat sat on the"):

```text
Backend returns token probabilities:
  " floor": 7.6%
  " bed": 6.5%
  " ground": 5.8%
  " table": 4.2%
  " couch": 3.1%
  " wall": 2.4%
  " chair": 1.8%
  " mat": 1.2%
  "<OTHER>": 67.4%

Frontend calculates wedge angles:
  " floor"  → 0.0° to 27.36°   (7.6% × 360 = 27.36°)
  " bed"    → 27.36° to 50.76° (6.5% × 360 = 23.4°)
  " ground" → 50.76° to 71.64° (5.8% × 360 = 20.88°)
  " table"  → 71.64° to 86.76° (4.2% × 360 = 15.12°)
  " couch"  → 86.76° to 97.92° (3.1% × 360 = 11.16°)
  " wall"   → 97.92° to 106.56° (2.4% × 360 = 8.64°)
  " chair"  → 106.56° to 113.04° (1.8% × 360 = 6.48°)
  " mat"    → 113.04° to 117.36° (1.2% × 360 = 4.32°)
  "<OTHER>" → 117.36° to 360.0° (67.4% × 360 = 242.64°)
```

#### Determining Selected Token from Wheel Rotation (Frontend)

**Goal**: After wheel spins, determine which token the pointer landed on

**Algorithm (Frontend - JavaScript)**:

```javascript
1. Generate random landing angle: landingAngle = Math.random() * 360

2. Animate wheel rotation:
   - totalRotation = (360 * 3) + landingAngle  // 3 full spins + landing
   - Apply CSS transform: rotate(totalRotation deg)

3. After animation completes, find selected wedge:
   - Pointer is fixed at top (0° position)
   - Wheel rotated clockwise by landingAngle
   - Wedge now under pointer was at: (360 - landingAngle) % 360
   - Find which wedge contains this angle

4. Return that wedge's token_id to backend

5. Backend processes token_id and returns selected token
```

**Example**:

```text
Wheel spins and lands at rotation: 344.5°

Calculation:
  - Pointer at top (0°)
  - Wheel rotated 344.5° clockwise
  - Wedge now at top was originally at: (360 - 344.5) = 15.5°
  - Check wedges: 15.5° falls in range 0.0° to 27.36°
  - This is the " floor" wedge (token_id: 1234)
  - Send token_id 1234 to backend
  - Backend returns " floor" as selected token
```

#### Dynamic Token Selection

Instead of fixed top-k, we use threshold-based selection with adaptive secondary threshold:

**Algorithm**:

```python
1. Get full probability distribution from model (softmax on logits)

2. Primary selection:
   - Include all tokens where probability ≥ min_threshold (default 0.01 = 1%)

3. Secondary selection (adaptive):
   - Calculate remaining_probability = 1.0 - sum(primary_tokens)
   - If remaining_probability > 0.2 (20%):
     * Also include tokens where probability ≥ secondary_threshold (default 0.005 = 0.5%)
     * Prevents "other" category from being too large

4. Calculate final remaining probability for "other"

5. Return token list + remaining probability
```

**Benefits**:

- Adapts to distribution shape
- Peaked distribution (clear winner) → fewer tokens, smaller "other"
- Flat distribution (model uncertain) → more tokens shown
- Prevents "other" from dominating in flat distributions
- More educationally honest about uncertainty

**Typical Results**:

- Peaked distribution: 8-12 tokens shown, "other" = 5-15%
- Flat distribution: 20-30 tokens shown, "other" = 10-20%

### Data Structures

#### Token Distribution

```python
{
    'tokens': [
        {
            'token': ' floor',
            'token_id': 1234,
            'probability': 0.076,
            'is_special': False
        },
        {
            'token': ' bed',
            'token_id': 5678,
            'probability': 0.065,
            'is_special': False
        },
        ...
    ],
    'remaining_probability': 0.674,  # for "other" category
    'context': 'The cat sat on the',
    'num_tokens': 8  # variable based on threshold
}
```

#### Token List (Backend Response)

```python
[
    {
        'token': ' floor',
        'token_id': 1234,
        'probability': 0.076,
        'is_special': False,
        'is_other': False
    },
    {
        'token': ' bed',
        'token_id': 5678,
        'probability': 0.065,
        'is_special': False,
        'is_other': False
    },
    ...
    {
        'token': '<OTHER>',
        'token_id': -1,
        'probability': 0.674,
        'is_special': False,
        'is_other': True
    }
]
```

#### Wedge Data (Frontend, after angle calculation)

```javascript
[
  {
    token: " floor",
    token_id: 1234,
    probability: 0.076,
    is_special: false,
    is_other: false,
    start_angle: 0.0, // Calculated by frontend
    end_angle: 27.36, // Calculated by frontend
  },
  {
    token: " bed",
    token_id: 5678,
    probability: 0.065,
    is_special: false,
    is_other: false,
    start_angle: 27.36,
    end_angle: 50.76,
  },
  ...{
    token: "<OTHER>",
    token_id: -1,
    probability: 0.674,
    is_special: false,
    is_other: true,
    start_angle: 117.36,
    end_angle: 360.0,
  },
];
```

#### Frontend State Shape

```typescript
// Frontend State Structure (TypeScript types for reference)

interface AppState {
  sessionId: string | null;
  currentContext: string;
  generatedTokens: string[];
  currentWedges: Wedge[];
  isSpinning: boolean;
  shouldContinue: boolean;
  step: number;
  selectionMode: "spin" | "manual";
  error: string | null;
}

interface Wedge {
  token: string;
  token_id: number;
  probability: number;
  start_angle: number;
  end_angle: number;
  is_special: boolean;
  is_other: boolean;
  color: string; // assigned by frontend
}
```

## Frontend Architecture

### Frontend Technology Stack

- **React 18+ with Vite**: UI framework and build tool
- **SVG**: Wheel rendering (crisp at any size, easy text labels, click handlers for manual selection)
- **CSS Transitions**: Spin animation (simple, performant)
- **Tailwind CSS**: Styling and responsive design
- **Native Fetch API**: Backend communication
- **React Hooks (useState, useContext)**: State management

### Required Components

#### 1. Wheel Visualization

**Rendering**:

- Circular wheel divided into wedge-shaped sections
- Each wedge sized exactly by probability (angle = probability × 360°)
- Different colors for each wedge (colorblind-friendly palette)
- Token labels on wedges (hoverable tooltips for small wedges)
- Probability percentages displayed
- Pointer/arrow at fixed position (top or right)

**Technical Approach**:

SVG implementation using path elements with arc commands for wedge shapes.

**Implementation approach**:

- Each wedge is an SVG `<path>` element with click handler
- Wedge colors use colorblind-friendly palette
- Labels positioned radially on wedges ≥10°
- Tooltips for wedges <10° (too small for readable labels)
- Special styling for "other" category (dashed border or pattern)
- Hover effects on wedges (opacity change for interactivity)

#### 2. Spin Animation

**Behavior**:

- Wheel rotates when user clicks "Spin" button
- Smooth rotation with realistic deceleration (ease-out)
- Landing angle is randomly generated on the frontend
- Animation duration: 3 seconds for good suspense
- Final position: pointer aligned with the wedge at the randomly chosen landing angle
- The landing angle determines which token is selected

**Note on Selection Modes**: Users can also manually select a token by clicking on a wedge directly, bypassing the spin animation entirely.

**Implementation Approach**:

**CSS Transform + Transition**:

- Wheel rotation controlled by CSS `transform: rotate()` property
- Smooth animation via CSS transition with cubic-bezier easing
- Rotation state managed by React useState
- For random spin: calculate random landing angle (0-360°)
- Apply rotation: `(360° × number_of_spins) + landing_angle`
- Duration: 3 seconds with `cubic-bezier(0.17, 0.67, 0.12, 0.99)` easing

```javascript
// Generate random landing angle
const landingAngle = Math.random() * 360;
const extraSpins = 3; // spin around 3 times for effect
const totalRotation = 360 * extraSpins + landingAngle;

// Apply to wheel element
wheelElement.style.transform = `rotate(${totalRotation}deg)`;
wheelElement.style.transition =
  "transform 3s cubic-bezier(0.17, 0.67, 0.12, 0.99)";

// After animation completes, send landingAngle to backend
```

**Manual Selection**:

- Click handlers on SVG path elements
- Immediate token selection (no animation)
- Optional: brief highlight animation on selected wedge
- Send `selected_token_id` directly to backend

#### 3. Token Selection Modes

The application supports two modes for selecting the next token:

**Spin Mode** (Random Probabilistic Selection):

- User clicks "Spin" button
- Wheel spins with random easing/duration variations for authenticity
- Landing angle is randomly generated: `landingAngle = Math.random() * 360`
- Wheel animates to land on the randomly chosen angle
- The wedge at that angle determines which token is selected
- Landing angle is sent to backend via `/api/select` endpoint
- Simulates the probabilistic nature of LLM token sampling

**Manual Selection Mode** (Deliberate Token Choice):

- User clicks directly on any wedge to select that token
- No spin animation occurs
- Selected token's ID is sent to backend via `/api/select` endpoint
- Allows students to explore alternative continuations
- Educational benefit: "What if I picked this less likely token instead?"
- Helps students understand how token choice affects subsequent generation

**Educational Value**:

Both modes serve important pedagogical purposes. Spin mode demonstrates the probabilistic nature of LLMs (tokens are sampled from a distribution), while manual selection mode gives students agency to explore the model's behavior by deliberately choosing different paths. This combination helps students understand both how LLMs typically generate text AND how different token choices lead to different outcomes.

#### 4. User Controls

**Components**:

- Text input for initial prompt
- "Start" button to begin generation
- "Spin" button to trigger random token selection
- Clickable wedges for manual token selection
- Display area showing generated text so far
- "Reset" button to start over
- Optional: Settings for auto-spin, animation speed

**Layout Structure**:

**Desktop (≥768px)**:

- Main content area: Centered wheel (600x600px)
- Left panel: Input prompt, Start/Reset buttons
- Right panel: Generated text display, token history
- Bottom: Spin button (during generation)

**Mobile (<768px)**:

- Stacked vertical layout
- Wheel at top (responsive size, min 300px)
- Controls below wheel
- Generated text at bottom
- Fixed "Spin" button at bottom of viewport

**Selection Mode Toggle**:

- Button to switch between "Spin Mode" and "Manual Selection"
- Visual indicator of current mode
- In manual mode, wedges show pointer cursor on hover

#### 5. State Management

**State Management Strategy**:

**Component-Local State (useState)**:

- Wheel rotation angle
- Animation state (isSpinning)
- UI controls (auto-spin enabled, animation speed)

**Shared State (useContext)**:

- Session ID
- Current context/generated text
- Current wedges array
- Generation history
- Selection mode (spin vs manual)

No global state library needed - React's built-in hooks are sufficient for this application scope.

**State Variables**:

```javascript
{
    sessionId: 'abc123',
    currentContext: 'The cat sat on the floor',
    generatedTokens: [' floor'],
    currentWedges: [...],
    isSpinning: false,
    shouldContinue: true,
    step: 1,
    selectionMode: 'spin', // 'spin' or 'manual'
    error: null
}
```

**State Flow**:

1. User enters prompt → POST /api/start → receive tokens with probabilities
2. Frontend calculates wedge angles from probabilities
3. Render wheel with wedges
4. User either:
   - Clicks "Spin" → generate random landing angle → animate wheel spin → calculate which wedge landed under pointer → get token_id
   - Clicks a wedge → get token_id directly
5. POST /api/select with selected_token_id
6. Receive selected token (actual token if "other" was selected) and next tokens
7. Frontend calculates new wedge angles
8. Display selected token and update context
9. Repeat steps 3-8 until shouldContinue = false

#### 6. Styling Approach

**Tailwind CSS**:

- Utility-first CSS framework for rapid development
- Responsive design with mobile-first breakpoints
- Consistent color palette and spacing
- Custom configuration for project-specific colors

**Component structure**:

- Layout: Flexbox/Grid for responsive positioning
- Wheel container: Fixed aspect ratio, centered
- Control panel: Bottom or side panel with buttons
- Text display: Scrollable area showing generated context

#### 7. API Integration

**Using native Fetch API with async/await**:

**Start Generation**:

- POST /api/start with user prompt
- → Receive session_id and initial wedges
- → Render wheel

**Token Selection (Spin Mode)**:

- User triggers spin → Generate random landing angle
- → Animate wheel rotation
- → Calculate which wedge is under pointer: (360 - rotation) % 360
- → Get token_id from selected wedge
- → POST /api/select with {session_id, selected_token_id}
- → Receive selected token and next tokens → Calculate wedge angles → Update display

**Token Selection (Manual Mode)**:

- User clicks wedge → Get token_id from wedge
- → POST /api/select with {session_id, selected_token_id}
- → Receive selected token and next tokens → Calculate wedge angles → Update display

**Error handling**:

- Network errors: Show retry button
- Session expired: Prompt user to restart
- Invalid responses: Log error, show user-friendly message

## Design Decisions & Rationale

### Why Spinner/Wheel Instead of Plinko?

**Problems with Plinko Approach**:

- Real Plinko physics creates fixed binomial distribution (center-biased)
- LLM probability distributions are variable (sometimes peaked, sometimes flat)
- Impossible to perfectly match physics distribution to arbitrary LLM distribution
- Required complex position mapping with approximation errors
- Physics simulation added complexity with little educational benefit

**Benefits of Wheel Approach**:

- **Perfect Accuracy**: Wedge size directly represents probability (no approximation)
- **Universal**: Works for ANY distribution shape (peaked, flat, multimodal)
- **Intuitive**: Everyone understands "bigger wedge = more likely"
- **Simpler**: No physics calculations, no distribution matching
- **Visual**: Probabilities immediately visible as wedge sizes
- **Still Engaging**: Spinning wheel is familiar, exciting, and suspenseful
- **Educational**: Direct 1:1 mapping between probability and visual representation

### Why Dynamic Token Selection?

**Instead of fixed top-k**:

- Adapts to distribution shape naturally
- Peaked distribution (clear winner) → fewer tokens shown
- Flat distribution (model uncertain) → more tokens shown
- Secondary threshold prevents "other" from dominating (>20% triggers more tokens)
- More educationally honest about model uncertainty
- No arbitrary cutoffs visible to students

**Typical Results**:

- Most generations: 10-20 tokens visible, "other" = 10-20%
- Very peaked: 5-10 tokens visible, "other" = 5-10%
- Very flat: 25-35 tokens visible, "other" = 15-25%

### Token Selection Design

**Decision**: Frontend determines token selection through wheel spin or user choice and always sends token_id to backend

**Rationale**:

- **Separation of Concerns**: Backend handles probabilities and token selection logic; Frontend handles all visual/angle calculations
- **User agency**: Students can either spin the wheel OR manually select a token by clicking a wedge
- **Educational value**: Lets students explore "what if I chose this token instead?" to understand how different token choices lead to different continuations
- **Authentic interaction**: The wheel spin actually determines the outcome - it's not a pre-determined animation
- **Simpler mental model**: What you see is what you get - the spin or click directly determines the selection
- **Exploration-friendly**: Students can experiment with less likely tokens to see alternative paths the model could have taken
- **Cleaner API**: Backend only needs to know which token was selected (by ID), not how it was selected

**Implementation**:

Both spin and manual modes ultimately send the same thing to the backend: a `token_id`. The difference is HOW the frontend determines which token_id:

- **Spin mode**: Random rotation → Calculate pointer position → Find wedge → Get token_id
- **Manual mode**: Click wedge → Get token_id directly

This design puts students in control of the generation process, making it more interactive and educational. They can experience both random probabilistic selection (via spin) and deliberate token choice (via manual selection).

### Why Frontend Calculates Wedge Angles

**Decision**: Frontend calculates wedge angles from probabilities; Backend only provides probabilities

**Rationale**:

- **Backend Simplification**: Backend focuses on its core responsibility (LLM inference and probability calculations)
- **No Angle Logic in Backend**: Backend doesn't need to know about wedges, angles, or visual representation
- **Frontend Control**: Frontend has full control over visual representation and can easily adjust wedge calculations if needed
- **Cleaner API**: API responses are simpler (just tokens and probabilities)
- **Easier Testing**: Backend can be tested without any angle-related logic
- **Single Source of Truth**: Frontend determines which token based on visual state it controls

### Why Session-Based API?

**Decision**: Stateful (session-based)

**Rationale**:

- Backend needs to maintain context across multiple token generations
- Caches model state for faster subsequent generations
- Avoids sending full context history in every request
- Simpler frontend logic
- Can support multiple concurrent users with separate sessions
- Easy to add session timeout and cleanup

**Trade-offs**:

- More complex server state management
- Need session storage (in-memory dict for MVP, Redis later if needed)
- Harder to scale horizontally (need sticky sessions or shared state store)

### Model Selection Strategy

#### Default Model: GPT-2

GPT-2 (124M parameters) is the default model for several reasons:

**Accessibility**:

- Runs on basic laptops with 4GB RAM
- Small download size (500MB)
- Fast inference even on older hardware
- Every student can use it regardless of their computer

**Reliability**:

- Mature, well-tested model
- Extensive documentation
- Known to work reliably in educational settings
- No authentication required

**Sufficient for Learning**:

- Demonstrates probabilistic token selection perfectly
- Shows clear probability distributions
- Quality good enough for educational purposes
- The mechanism is the lesson, not the output quality

#### Alternative Model: TinyLlama 1.1B

TinyLlama 1.1B (1.1B parameters) is included as a modern alternative:

**Educational Value**:

- Shows that the token selection mechanism is universal across different model architectures
- Produces noticeably different probability distributions for the same context
- Demonstrates how model architecture affects output (GPT-2 vs Llama)
- Allows students to compare "old" (2019) vs "new" (2024) model behavior

**Quality Comparison**:

- Better coherence than GPT-2
- More modern training data
- Different tokenization approach
- Still small enough to run locally

**Accessibility Considerations**:

- Requires 4GB RAM (vs 2GB for GPT-2)
- Larger download (2.2GB vs 500MB)
- No authentication required (ungated model)
- More accessible than larger models like Llama 3.2

#### Why Support Both?

Having two models pre-loaded serves multiple educational goals:

**Universal Mechanism Demonstration**:

- Students see that the probability wheel works identically for both models
- The wedge size = probability relationship holds regardless of model
- Same codebase, same visualization, different underlying model
- Reinforces: "This is how ALL autoregressive LLMs work"

**Practical Comparison**:

- Students can generate the same prompt with both models
- Compare probability distributions side-by-side
- See how GPT-2 might favor different tokens than Llama
- Understand that model choice affects output, but not the mechanism

**Hardware Flexibility**:

- Students with basic laptops use GPT-2 (everyone can participate)
- Students with better hardware can explore TinyLlama (enrichment opportunity)
- No one is excluded from core learning objectives

**Future-Proofing**:

- Demonstrates the architecture is model-agnostic
- Sets precedent for adding more models later
- Shows students that "ChatGPT" is just one model among many

### Why All Through Hugging Face Transformers?

**Consistency**:

- Single unified interface (`AutoModelForCausalLM`) works for all models
- Same loading pattern, same inference API
- Reduces code complexity and maintenance burden

**No External Dependencies**:

- Everything runs locally on the Docker container
- No API keys, rate limits, or internet required during use
- No API costs for the university or students
- Models downloaded once during Docker build, then cached

**Educational Transparency**:

- Students see actual model inference, not black-box API calls
- Can examine tokenization, logits, probabilities directly
- Demystifies how LLMs work under the hood
- Supports learning objectives around model internals

**Extensibility**:

- Hugging Face has 500,000+ models available
- Adding new models is trivial (update config, rebuild Docker)
- Can easily support GPT-Neo, Mistral, Phi, or other models later
- Future-proof architecture

### Why Pre-load Both Models in Docker?

**User Experience**:

- Students can switch between models instantly
- No waiting for downloads during class
- Works offline (important for spotty classroom wifi)
- Predictable behavior across all deployments

**Educational Flow**:

- Instructor can demo both models without delays
- Students can experiment freely without download anxiety
- Side-by-side comparisons happen in real-time
- No "it's still downloading" interruptions during lessons

**Deployment Simplicity**:

- Single Docker image contains everything needed
- No runtime model management complexity
- Cloud deployment is straightforward
- Consistent behavior: dev = staging = production

**Trade-off Accepted**:

- Larger Docker image (~3-4 GB vs ~1 GB)
- Longer initial build/pull time
- Worth it for instant model switching and offline capability
- Storage is cheap, student time is valuable

## Known Limitations

### 0. Model Resource Requirements

**Issue**: Different models have significantly different resource requirements

**Impact**:

- **GPT-2**: 2GB RAM - accessible to all students (even basic laptops)
- **TinyLlama 1.1B**: 4GB RAM - accessible to most modern systems
- Students with only 4GB total RAM can only use GPT-2
- Docker image size: 3-4GB (includes both pre-loaded models)

**Educational Consideration**: This limitation itself becomes a teaching moment:

- Demonstrates real-world computational costs of AI
- Shows why model size matters for deployment
- Explains why many AI services use APIs (centralized compute)
- Illustrates trade-offs between model quality and accessibility

**Mitigation**:

- GPT-2 is the default and works for everyone
- UI clearly shows RAM requirements before switching models
- TinyLlama is an optional enrichment, not required
- Cloud deployment can support both models for all students

### 1. Token vs Word

**Issue**: GPT-2 uses Byte-Pair Encoding (BPE), so tokens don't always align with words

**Examples**:

- "unhappy" → [" un", "happy"]
- "tokenization" → [" token", "ization"]
- "GPT-2" → [" G", "PT", "-", "2"]

**Impact**: Students might be confused initially when they see partial words on the wheel

**Mitigation**: Brief explanation in UI about what "tokens" are

### 2. "Other" Category

**Issue**: Some probability mass grouped into "other" wedge

**Justification**:

- Tokens <1% (or <0.5%) are too small to visualize clearly
- Wedges <2-3° are hard to see and label
- "Other" typically represents truly negligible options
- Still more honest than hiding them completely

**Handling**:

- When "other" is selected, backend samples from remaining distribution and returns the actual token (not the literal string "OTHER")
- This ensures students see real tokens even when selecting from the "other" category
- Could show "other" details in expandable tooltip (advanced feature)

### 3. Wedge Visibility

**Issue**: Small probabilities (<1-2%) create tiny wedges that are hard to see/label

**Solutions**:

- Dynamic threshold ensures most wedges are reasonably sized
- Tooltips/hover for small wedges
- Separate legend/table showing all tokens and probabilities
- Consider minimum visual wedge size (even if slightly distorts probabilities)

### 4. Label Overlap

**Issue**: Many tokens might make labels crowded/overlapping

**Solutions**:

- Show labels only on wedges above certain size threshold
- Use tooltips for smaller wedges
- Radial text placement along wedge arc
- Separate token probability table alongside wheel

### 5. Generation Quality

**Issue**: GPT-2 is not as good as modern models (GPT-4, Claude, etc.)

**Impact**: Outputs sometimes incoherent or repetitive

**Justification**:

- Students are learning the _mechanism_, not evaluating quality
- Good enough for demonstration purposes
- Coherent enough to be interesting
- Can upgrade to better models later

### 6. Token vs Word Mismatch (Educational)

**Issue**: Students expect words, but see BPE tokens

**Mitigation**:

- Clear explanation upfront about tokenization
- Visual highlighting when token completes a word
- Consider this a learning opportunity about how LLMs actually work

## References

- [Hugging Face Transformers Documentation](https://huggingface.co/docs/transformers/)
- [GPT-2 Paper](https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PyTorch Documentation](https://pytorch.org/docs/stable/index.html)
- [BPE Tokenization Explained](https://huggingface.co/learn/nlp-course/chapter6/5)
