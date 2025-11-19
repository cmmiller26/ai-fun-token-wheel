# AGENTS.md - Project Context for AI Assistants

## Project Overview

**Project Name**: AI FUN Token Wheel - Visual Language Model Token Generation

**Purpose**: An educational demonstration tool for the AI Fundamentals course (CSI:1234) at the University of Iowa. This project visualizes how Large Language Models generate text by representing the probabilistic token selection process as a spinning probability wheel.

**Academic Context**:

- Part of a new undergraduate AI certificate program
- Co-taught by Dr. Tyler Bell (Engineering) and Dr. Ali Hasan (Philosophy)
- Target audience: Students from all majors, no technical prerequisites required
- Focus: Hands-on AI tools + ethical implications

**Constraints**:

- Must run locally (no API costs)
- Must be accessible to non-technical students
- Must be visually engaging

## Core Concept

The key educational insight: **LLMs don't deterministically choose the next word - they sample from a probability distribution.**

Students see the probability distribution visualized as a spinning wheel, where:

- The wheel is divided into wedge-shaped sections
- Each token gets a wedge sized exactly proportional to its probability
- Wedge angle = (token_probability / 1.0) × 360°
- Larger wedges = higher probability = more likely to be selected
- The wheel spins and a pointer lands on a wedge
- The token in that wedge is selected and added to the text
- This process repeats for each token in the generated text

**Critical Design Choice**: The backend selects the token first, then the frontend animates the wheel to land on that result. This ensures perfect probability accuracy while maintaining engaging visualization. The wheel animation reflects the actual probabilistic sampling that occurred.

**Key Insight**: The wheel provides a perfectly accurate visualization of probabilities - wedge size directly represents token probability. Unlike physics-based approaches, this works for any probability distribution shape (peaked, flat, or anything in between) with zero approximation error.

## Documentation

For all technical implementation details, read **`docs/ARCHITECTURE.md`**, which contains:

- Backend architecture and implementation details
- API endpoint designs
- Core algorithms (wedge allocation, token sampling)
- Data structures and data flow
- Frontend architecture basics
- Design decisions and rationale

## Development Guidelines

**Key reminders when coding**:

- This is an educational tool - clarity > perfect accuracy
- Target audience is non-technical - avoid jargon in UI
- Preserve the "wedge size = probability" concept - it's central to the pedagogy
- When suggesting improvements, ask: "Does this help students understand LLMs better?"

**Educational goals students should understand**:

1. LLMs generate text one token at a time
2. Each token is chosen probabilistically, not deterministically
3. Context affects probability distribution (same prompt prefix → different continuations possible)
4. The model doesn't "know" what it will say next - it's sampling at each step
5. Wedge size directly represents probability - bigger wedge = more likely selection
