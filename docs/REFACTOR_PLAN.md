# Refactoring and Improvement Plan

This document outlines the current architectural issues in the `ai-fun-token-wheel` codebase and proposes a series of steps to refactor the application for better performance, maintainability, and user experience.

## Summary of Issues

The application is a creative and effective educational tool, but the underlying implementation has several architectural weaknesses that should be addressed.

### Backend Issues

1. **Critical Performance Bottleneck**: The GPT-2 model is loaded into memory every time a user starts a new "session." This is highly inefficient, causing a significant delay at the beginning of each interaction and consuming excessive memory.
2. **Fragile Session Management**: User session data is stored in a global, in-memory Python dictionary. This data is not persistent (lost on server restart) and is not safe for concurrent access, making it unsuitable for any multi-user scenario.
3. **Outdated Tests**: The unit tests for the backend are written for a previous version of the code and do not accurately reflect the current API, rendering them ineffective for ensuring code quality.
4. **No `.gitignore`**: The Python virtual environment (`.venv/`) is currently tracked by version control, which is not standard practice and bloats the repository.

### Frontend Issues

1. **Overloaded Main Component**: The primary `App.jsx` component manages all of the application's state and logic. This "god component" pattern makes the code difficult to read, maintain, and test.
2. **Prop Drilling**: State and handler functions are passed down through multiple layers of components, a pattern known as "prop drilling." This makes component reuse difficult and complicates an understanding of data flow.
3. **Suboptimal User Experience (UX)**: The UI does not provide clear feedback to the user during asynchronous operations (like waiting for the backend) or when errors occur.

## Proposed Refactoring Plan

The following steps are proposed to address these issues. The backend should be addressed first to create a stable foundation.

### Phase 1: Backend Refactoring

1. **Implement Singleton Model Loading**:
    * **Action**: Modify `backend/main.py` to use FastAPI's `lifespan` context manager.
    * **Goal**: Load the `GPT2TokenWheelGenerator` once when the application starts up and store it as a shared, global instance. This will eliminate the per-request loading delay.

2. **Create a Stateless API**:
    * **Action**: Remove the session-based logic (`/api/start`, `/api/select`, the `sessions` dictionary).
    * **Goal**: Replace the multi-step process with a single, stateless API endpoint (e.g., `/api/generate`). This endpoint will accept the current text prompt and return the next token probabilities in one call, dramatically simplifying the backend logic.

3. **Update Unit Tests**:
    * **Action**: Rewrite the tests in `backend/tests/` to align with the new stateless API.
    * **Goal**: Ensure the new `/api/generate` endpoint is properly tested for correct responses and error handling.

4. **Add `.gitignore`**:
    * **Action**: Create a `.gitignore` file in the `backend/` directory.
    * **Goal**: Exclude the `.venv/` and `__pycache__/` directories from version control.

### Phase 2: Frontend Refactoring

1. **Update API Service**:
    * **Action**: Modify `frontend/src/services/api.js`.
    * **Goal**: Replace the old `start` and `select` functions with a single function that calls the new stateless `/api/generate` backend endpoint.

2. **Create Custom Hooks**:
    * **Action**: Create a `frontend/src/hooks/` directory and add a custom hook (e.g., `useTokenWheel.js`).
    * **Goal**: Encapsulate all application logic and state management (API calls, loading status, error handling, prompt state) within this hook to decouple it from the UI.

3. **Simplify `App.jsx`**:
    * **Action**: Refactor `App.jsx` to use the new `useTokenWheel` hook.
    * **Goal**: Remove the complex state and logic from `App.jsx`, turning it into a much cleaner component primarily responsible for layout and rendering.

4. **Improve User Experience**:
    * **Action**: Use the `isLoading` and `error` states from the custom hook.
    * **Goal**: Display loading indicators in the UI while waiting for the API, disable buttons to prevent duplicate requests, and show user-friendly messages when errors occur.
