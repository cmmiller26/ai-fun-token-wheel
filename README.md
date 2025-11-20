# AI FUN Token Wheel

An educational visualization tool that demonstrates how Large Language Models generate text by representing the probabilistic token selection process as an interactive spinning probability wheel.

## Overview

**AI FUN Token Wheel** is designed for the AI Fundamentals course (CSI:1040) at the University of Iowa. It provides students with a hands-on, visual understanding of how LLMs work under the hood - specifically, how they probabilistically sample the next token from a distribution rather than deterministically choosing it.

### Key Educational Concepts

Students learn that:

1. LLMs generate text **one token at a time**
2. Each token is chosen **probabilistically**, not deterministically
3. Context affects the probability distribution
4. The model doesn't "know" what it will say next - it samples at each step
5. **Wedge size directly represents probability** - bigger wedge = more likely selection

## How It Works

The application visualizes token generation as a probability wheel:

- The wheel is divided into wedge-shaped sections
- Each wedge represents a possible next token
- **Wedge angle is proportional to token probability**: `angle = (probability / 1.0) × 360°`
- Users can either:
  - **Spin the wheel** to randomly select a token (simulating LLM sampling)
  - **Click a wedge** to manually explore alternative paths
- The selected token is added to the context
- A new wheel is generated based on the updated context
- The process repeats to build complete text

## Architecture

The application uses a **unified Docker architecture**:

- **Single container** combines both frontend and backend
- **Frontend**: React/Vite application (built to static files)
- **Backend**: Python/FastAPI server
  - Loads and runs GPT-2 model locally (no API costs)
  - Calculates token probabilities via model inference
  - Serves both API endpoints and frontend static files
  - Manages generation sessions and context

For detailed architecture information, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Features

- Interactive probability wheel with accurate probability-to-wedge-size mapping
- Two selection modes:
  - **Spin Mode**: Random probabilistic selection (authentic LLM behavior)
  - **Manual Mode**: Click to select any token (explore alternatives)
- Dynamic token selection with adaptive thresholds
- "Other" category for low-probability tokens
- Real-time text generation visualization
- Session-based API for multiple concurrent users
- Responsive design for desktop and mobile

## Getting Started

### Prerequisites

- **Docker** and **Docker Compose** (recommended)
  - OR:
- **Python 3.11+** (for backend)
- **Node.js 20+** (for frontend)

### Quick Start with Docker

The easiest way to run the project:

```bash
# Clone the repository
git clone <repository-url>
cd ai-fun-token-wheel

# Build and start the application
docker compose up --build
```

Access the application:

- **Application:** <http://localhost:8000>
- **API Documentation:** <http://localhost:8000/docs>

The first run will download the GPT-2 model (~500MB), which is cached for future runs.

For detailed local development and production deployment instructions, see [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

### Manual Setup (Without Docker)

#### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend available at <http://localhost:8000>

#### Frontend Setup

```bash
# Navigate to frontend directory (in a new terminal)
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend available at <http://localhost:5173> (Vite dev server)

**Note**: When running separately, the frontend automatically proxies `/api` requests to <http://localhost:8000>.

### Stopping the Application

If using Docker:

```bash
# Stop services
docker compose down

# Stop and remove cached models
docker compose down -v
```

If running manually, press `Ctrl+C` in each terminal.

## Usage

1. **Enter a prompt**: Type a starting text (e.g., "The cat sat on the")
2. **Click "Start Generation"**: The backend calculates token probabilities and displays the wheel
3. **Select a token**:
   - Click **"Spin"** to randomly select based on probabilities
   - Or **click a wedge** directly to choose that token
4. **Watch the generation**: The selected token is added to your text
5. **Continue**: A new wheel appears with updated probabilities
6. **Repeat**: Keep selecting tokens to build your text
7. **Reset**: Click "Reset" to start over with a new prompt

### Educational Tips

- Try different prompts to see how context affects probabilities
- Compare spinning (random) vs. manual selection to understand sampling
- Notice how wedge sizes change as context evolves
- Explore the "Other" category to see less likely options
- Observe how certain contexts create peaked distributions (clear winner) vs. flat distributions (model uncertainty)

## Project Structure

```text
ai-fun-token-wheel/
├── backend/
│   ├── main.py              # FastAPI server and endpoints
│   ├── generator.py         # GPT-2 model wrapper
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Main React component
│   │   └── ...
│   └── package.json        # Node dependencies
├── docs/
│   ├── ARCHITECTURE.md     # Detailed technical documentation
│   └── DEPLOYMENT.md       # Deployment guide
├── Dockerfile              # Unified container build
├── docker-compose.yml      # Local orchestration
└── README.md              # This file
```

## API Endpoints

The backend provides the following REST API endpoints:

- `POST /api/start` - Start a new generation session
- `POST /api/spin` - Sample a token from the current distribution
- `POST /api/select` - Select a token and get next distribution
- `GET /api/session/{session_id}` - Get session state
- `DELETE /api/session/{session_id}` - Delete a session
- `GET /api/health` - Health check

For detailed API documentation, visit <http://localhost:8000/docs> when the backend is running.

## Technologies Used

### Backend

- **Python 3.11**: Core language
- **FastAPI**: Modern async web framework
- **PyTorch**: Deep learning framework (CPU-only for efficiency)
- **Transformers**: Hugging Face library for GPT-2
- **Uvicorn**: ASGI server

### Frontend

- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **Tailwind CSS**: Utility-first styling
- **SVG**: Wheel rendering
- **Axios**: HTTP client

### Infrastructure

- **Docker & Docker Compose**: Containerization
- **GitHub Container Registry**: Container image hosting
- **GitHub Actions**: CI/CD pipeline

## Development

### Local Development with Hot-Reloading

**Backend:**

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

The `--reload` flag enables hot-reloading on code changes.

**Frontend:**

```bash
cd frontend
npm run dev
```

Vite provides hot module replacement (HMR) for instant updates.

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Configuration

### Backend Configuration

Configuration options can be passed in the `/api/start` request:

- `min_threshold`: Primary probability threshold (default: 0.01 = 1%)
- `secondary_threshold`: Secondary threshold for flat distributions (default: 0.005 = 0.5%)
- `model`: GPT-2 model variant (default: "gpt2")

### Frontend Configuration

Environment variables can be set in `.env` files:

- `VITE_API_URL`: Backend API URL (automatically set during Docker build)

## Known Limitations

1. **Token vs Word**: GPT-2 uses Byte-Pair Encoding, so tokens may be sub-words
2. **"Other" Category**: Low-probability tokens (<1%) are grouped into an "Other" wedge
3. **Small Wedges**: Very small probabilities create tiny wedges that are hard to read (tooltips help)
4. **Generation Quality**: GPT-2 is not as advanced as GPT-4/Claude, but sufficient for educational purposes
5. **Local Resources**: Requires ~2GB RAM for model inference

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for detailed discussion of design decisions and trade-offs.

## Deployment

### Docker Image Publishing

The project includes GitHub Actions that automatically build and publish Docker images to GitHub Container Registry on every push to the `main` branch.

**Using pre-built images:**

```bash
# Pull the latest image
docker pull ghcr.io/YOUR_USERNAME/ai-fun-token-wheel:main

# Run locally
docker run -p 8000:8000 ghcr.io/YOUR_USERNAME/ai-fun-token-wheel:main
```

### Production Deployment

The containerized application can be deployed to any Docker-compatible platform:

- **Docker-based platforms**: Railway, Render, Fly.io, Digital Ocean, AWS ECS, Azure Container Instances
- **Your own server**: Any machine running Docker

For complete deployment instructions and platform-specific guidance, see [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Troubleshooting

### Model not loading

The first run downloads GPT-2 (~500MB). This is cached in Docker volumes or `~/.cache/huggingface/`.

### Port conflicts

Modify port in `docker compose.yml`:

```yaml
ports:
  - "YOUR_PORT:8000"
```

### Memory issues

Ensure Docker has at least 2GB RAM allocated (Docker Desktop → Settings → Resources).

### Connection refused

Check that the service is running:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs app
```

## Contributing

This is an educational project for CSI:1040 at the University of Iowa. Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Academic Context

**Course**: AI Fundamentals (CSI:1040)
**Institution**: University of Iowa
**Instructors**: Dr. Tyler Bell (Engineering) and Dr. Ali Hasan (Philosophy)
**Target Audience**: Undergraduate students from all majors (no technical prerequisites)

This tool is part of a broader curriculum covering hands-on AI tools and ethical implications of artificial intelligence.

## License

This project is created for educational purposes at the University of Iowa.

## Acknowledgments

- Built with Hugging Face Transformers and GPT-2
- Inspired by the need to make LLM internals accessible to non-technical students
- Thanks to the open-source community for PyTorch, React, and FastAPI

## Support

For issues or questions:

1. Check [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for technical details
2. Review [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for deployment help
3. Review the troubleshooting section above
4. Open an issue on the repository

---

**Educational Focus**: This tool prioritizes clarity and engagement over perfect accuracy. The goal is to help students understand the core concept of probabilistic token selection in LLMs through an interactive, visual interface.
