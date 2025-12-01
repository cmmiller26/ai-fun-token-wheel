import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

/**
 * Start a new token generation session
 * @param {string} prompt - Initial prompt text
 * @param {string} model - Model name (default: 'gpt2')
 * @param {number} min_threshold - Minimum probability threshold (optional, uses backend default)
 * @param {number} secondary_threshold - Secondary threshold for "other" wedge (optional, uses backend default)
 * @returns {Promise} Session data with initial wedges
 */
export const startGeneration = async (
  prompt,
  model = 'gpt2',
  min_threshold = undefined,
  secondary_threshold = undefined
) => {
  const requestBody = {
    prompt,
    model,
  };

  // Only include thresholds if explicitly provided
  if (min_threshold !== undefined) {
    requestBody.min_threshold = min_threshold;
  }
  if (secondary_threshold !== undefined) {
    requestBody.secondary_threshold = secondary_threshold;
  }

  const response = await axios.post(`${API_BASE_URL}/api/start`, requestBody);
  return response.data;
};

/**
 * Tell the backend to spin the wheel and sample a token
 * @param {string} sessionId - Session ID
 * @returns {Promise} Sampled token data including target_angle
 */
export const spinWheel = async (sessionId) => {
  const response = await axios.post(`${API_BASE_URL}/api/spin`, {
    session_id: sessionId,
  });
  return response.data;
};

/**
 * Select the next token in the generation
 * @param {string} sessionId - Session ID
 * @param {number} selectedTokenId - Token ID of the selected token
 * @returns {Promise} Selected token data and next state
 */
export const selectToken = async (sessionId, selectedTokenId) => {
  const response = await axios.post(`${API_BASE_URL}/api/select`, {
    session_id: sessionId,
    selected_token_id: selectedTokenId,
  });
  return response.data;
};

/**
 * Get current session state
 * @param {string} sessionId - Session ID
 * @returns {Promise} Session state
 */
export const getSession = async (sessionId) => {
  const response = await axios.get(`${API_BASE_URL}/api/session/${sessionId}`);
  return response.data;
};

/**
 * Delete a session
 * @param {string} sessionId - Session ID
 * @returns {Promise} Deletion confirmation
 */
export const deleteSession = async (sessionId) => {
  const response = await axios.delete(`${API_BASE_URL}/api/session/${sessionId}`);
  return response.data;
};

/**
 * Get list of available models
 * @returns {Promise} List of models with availability status
 */
export const getModels = async () => {
  const response = await axios.get(`${API_BASE_URL}/api/models`);
  return response.data;
};