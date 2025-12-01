import { useState, useEffect } from 'react';
import { startGeneration, spinWheel, selectToken, deleteSession, getModels } from '../services/api';
import { calculateWedgeAngles } from '../utils/wedgeCalculations';

/**
 * Custom hook for managing token wheel state and logic
 *
 * This hook encapsulates all business logic for the token wheel application:
 * - Session management
 * - API calls and error handling
 * - Wedge calculations
 * - Spin and manual selection logic
 * - Loading states
 */
export const useTokenWheel = () => {
  // Core state
  const [sessionId, setSessionId] = useState(null);
  const [currentContext, setCurrentContext] = useState('');
  const [generatedTokens, setGeneratedTokens] = useState([]);
  const [currentWedges, setCurrentWedges] = useState([]);
  const [step, setStep] = useState(0);
  const [shouldContinue, setShouldContinue] = useState(true);

  // Model selection state
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);
  const [currentSessionModel, setCurrentSessionModel] = useState(null);

  // Selection mode state
  const [selectionMode, setSelectionMode] = useState('spin'); // 'spin' | 'manual'

  // UI state
  const [isLoading, setIsLoading] = useState(false);
  const [isSpinning, setIsSpinning] = useState(false);
  const [error, setError] = useState(null);

  // Animation state
  const [selectedTokenInfo, setSelectedTokenInfo] = useState(null);
  const [highlightedWedgeIndex, setHighlightedWedgeIndex] = useState(null);
  const [showTokenPop, setShowTokenPop] = useState(false);
  const [triggerPointerBounce, setTriggerPointerBounce] = useState(false);
  const [spinResult, setSpinResult] = useState(null); // To store result from /api/spin

  /**
   * Load available models on mount
   */
  useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await getModels();
        setAvailableModels(response.models);

        // Set default model (prefer default, fallback to first available)
        const defaultModel = response.models.find(m => m.is_default && m.available)
                             || response.models.find(m => m.available);

        if (defaultModel) {
          setSelectedModel(defaultModel.key);
        }
      } catch (err) {
        console.error('Error loading models:', err);
        setError('Failed to load models');
      }
    };

    loadModels();
  }, []);

  /**
   * Start a new generation session
   * @param {string} prompt - Initial prompt text
   */
  const handleStartGeneration = async (prompt) => {
    if (!prompt.trim()) {
      setError('Please enter a prompt');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Pass selected model to API
      const response = await startGeneration(prompt, selectedModel);

      // Calculate wedge angles from token probabilities
      const wedges = calculateWedgeAngles(response.tokens);

      setSessionId(response.session_id);
      setCurrentContext(response.context);
      setCurrentWedges(wedges);
      setStep(response.step);
      setShouldContinue(true);
      setGeneratedTokens([]);

      // Store which model this session is using
      setCurrentSessionModel(response.model);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message;
      if (err.code === 'ERR_NETWORK') {
        setError('Unable to connect to server. Please ensure the backend is running.');
      } else if (err.response?.status === 500) {
        setError('An error occurred during generation. Please try again.');
      } else {
        setError(`Failed to start generation: ${errorMessage}`);
      }
      console.error('Error starting generation:', err);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle spinning the wheel (calls backend to get spin result)
   */
  const handleSpin = async () => {
    if (!sessionId || isSpinning || !shouldContinue) {
      return;
    }

    setIsSpinning(true);
    setError(null);

    try {
      // Call backend to get the real, probabilistic spin result
      const result = await spinWheel(sessionId);
      setSpinResult(result); // Store result, including token_id and target_angle
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message;
      if (err.code === 'ERR_NETWORK') {
        setError('Unable to connect to server. Please try again.');
      } else if (err.response?.status === 404) {
        setError('Your session has expired. Please start a new generation.');
      } else {
        setError(`Failed to spin wheel: ${errorMessage}`);
      }
      console.error('Error spinning wheel:', err);
      setIsSpinning(false); // Stop spinning on error
    }
  };

  /**
   * Handle when spin animation completes
   */
  const handleSpinComplete = async () => {
    if (!spinResult) {
      console.error("Spin complete called without a spin result. This shouldn't happen.");
      setIsSpinning(false);
      return;
    }

    try {
      const { token: selected_token, token_id, probability, target_angle, is_other } = spinResult;

      // Find the wedge that contains this token
      let selectedWedgeIndex = currentWedges.findIndex(w => w.token_id === token_id);

      // If token not found (it was sampled from "other"), find the "other" wedge
      if (selectedWedgeIndex === -1 && is_other) {
        selectedWedgeIndex = currentWedges.findIndex(w => w.is_other === true);
      }

      console.log('=== SPIN COMPLETE ===');
      console.log('Selected token:', selected_token);
      console.log('Token ID:', token_id);
      console.log('Is from "other":', is_other);
      console.log('Target angle from backend:', target_angle);
      console.log('Selected wedge index:', selectedWedgeIndex);
      if (selectedWedgeIndex >= 0) {
        const wedge = currentWedges[selectedWedgeIndex];
        console.log('Wedge angles:', wedge.start_angle, '-', wedge.end_angle);
      }
      console.log('All wedges:', currentWedges.map(w => `${w.token}: ${w.start_angle.toFixed(1)}-${w.end_angle.toFixed(1)}`));
      console.log('====================');

      // Trigger visual feedback immediately
      setHighlightedWedgeIndex(selectedWedgeIndex);
      setTriggerPointerBounce(true);

      // Reset pointer bounce after animation
      setTimeout(() => setTriggerPointerBounce(false), 500);

      // Call the backend to CONFIRM the token selection and advance the state
      const response = await selectToken(sessionId, token_id);

      // Store selected token info for the pop-up animation
      setSelectedTokenInfo({
        token: selected_token,
        probability: probability,
        wedgeIndex: selectedWedgeIndex
      });
      setShowTokenPop(true);

      // Wait for highlight duration (2000ms) before proceeding
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Clear visual feedback first
      setShowTokenPop(false);
      setHighlightedWedgeIndex(null);
      setSelectedTokenInfo(null);

      // Small delay to let animations complete
      await new Promise(resolve => setTimeout(resolve, 200));

      // Update state with the selected token and new context
      setCurrentContext(response.new_context);
      setGeneratedTokens([...generatedTokens, response.selected_token]);
      setShouldContinue(response.should_continue);
      setStep(response.step);
      setIsSpinning(false);
      setSpinResult(null); // Reset the spin result

      // If generation should continue, calculate new wedges
      if (response.should_continue) {
        const wedges = calculateWedgeAngles(response.next_tokens);
        setCurrentWedges(wedges);
      }
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message;
      if (err.code === 'ERR_NETWORK') {
        setError('Unable to connect to server. Please try again.');
      } else if (err.response?.status === 404) {
        setError('Your session has expired. Please start a new generation.');
      } else {
        setError(`Failed to select token: ${errorMessage}`);
      }
      console.error('Error selecting token:', err);
      setIsSpinning(false);
    }
  };

  /**
   * Handle manual wedge click
   * @param {Object} wedge - The wedge that was clicked
   */
  const handleManualSelection = async (wedge) => {
    if (!sessionId || isSpinning || !shouldContinue) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const selectedWedgeIndex = currentWedges.findIndex(w => w.token_id === wedge.token_id);

      // Trigger visual feedback immediately
      setHighlightedWedgeIndex(selectedWedgeIndex);
      setTriggerPointerBounce(true);

      // Reset pointer bounce after animation
      setTimeout(() => setTriggerPointerBounce(false), 500);

      // Call the backend to select the token using token ID
      const response = await selectToken(sessionId, wedge.token_id);

      // Store selected token info and show pop animation
      // Use the probability from the response (important for "other" tokens which get sampled)
      setSelectedTokenInfo({
        token: response.selected_token,
        probability: response.selected_token_probability,
        wedgeIndex: selectedWedgeIndex
      });
      setShowTokenPop(true);

      // Wait for highlight duration (2000ms) before proceeding
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Clear visual feedback first
      setShowTokenPop(false);
      setHighlightedWedgeIndex(null);
      setSelectedTokenInfo(null);

      // Small delay to let animations complete
      await new Promise(resolve => setTimeout(resolve, 200));

      // Update state with the selected token and new context
      setCurrentContext(response.new_context);
      setGeneratedTokens([...generatedTokens, response.selected_token]);
      setShouldContinue(response.should_continue);
      setStep(response.step);
      setIsLoading(false);

      // If generation should continue, calculate new wedges
      if (response.should_continue) {
        const wedges = calculateWedgeAngles(response.next_tokens);
        setCurrentWedges(wedges);
      }
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message;
      if (err.code === 'ERR_NETWORK') {
        setError('Unable to connect to server. Please try again.');
      } else if (err.response?.status === 404) {
        setError('Your session has expired. Please start a new generation.');
      } else {
        setError(`Failed to select token: ${errorMessage}`);
      }
      console.error('Error selecting token:', err);
      setIsLoading(false);
    }
  };

  /**
   * Reset generation and clear all state
   */
  const handleResetGeneration = async () => {
    // Optionally delete the session on the backend
    if (sessionId) {
      try {
        await deleteSession(sessionId);
      } catch (err) {
        console.error('Error deleting session:', err);
        // Continue with reset even if deletion fails
      }
    }

    // Clear all state
    setSessionId(null);
    setCurrentContext('');
    setCurrentWedges([]);
    setSelectedTokenInfo(null);
    setGeneratedTokens([]);
    setIsSpinning(false);
    setShouldContinue(true);
    setStep(0);
    setError(null);
    setSelectionMode('spin');
    setHighlightedWedgeIndex(null);
    setShowTokenPop(false);
    setTriggerPointerBounce(false);
    setSpinResult(null);
    setCurrentSessionModel(null); // Clear current session model
  };

  /**
   * Clear error message
   */
  const clearError = () => {
    setError(null);
  };

  /**
   * Set selection mode (spin or manual)
   * @param {string} mode - 'spin' | 'manual'
   */
  const handleSetSelectionMode = (mode) => {
    setSelectionMode(mode);
  };

  // Return public API of the hook
  return {
    // State
    sessionId,
    currentContext,
    generatedTokens,
    currentWedges,
    isLoading,
    isSpinning,
    error,
    shouldContinue,
    step,
    selectionMode,
    selectedTokenInfo,
    highlightedWedgeIndex,
    showTokenPop,
    triggerPointerBounce,
    spinResult,

    // Model state
    availableModels,
    selectedModel,
    currentSessionModel,

    // Actions
    startGeneration: handleStartGeneration,
    spin: handleSpin,
    handleSpinComplete,
    selectToken: handleManualSelection,
    resetGeneration: handleResetGeneration,
    setSelectionMode: handleSetSelectionMode,
    setSelectedModel,
    clearError,
  };
};
