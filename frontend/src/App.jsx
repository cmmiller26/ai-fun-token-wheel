import React, { useState } from 'react';
import PromptInput from './components/PromptInput';
import TokenWheel from './components/TokenWheel';
import SpinControls from './components/SpinControls';
import GeneratedText from './components/GeneratedText';
import ResetButton from './components/ResetButton';
import TokenProbabilityTable from './components/TokenProbabilityTable';
import { startGeneration, spinWheel, selectToken, deleteSession } from './services/api';
import { calculateWedgeAngles, findTokenByAngle } from './utils/wedgeCalculations';

function App() {
  // State management
  const [sessionId, setSessionId] = useState(null);
  const [currentContext, setCurrentContext] = useState('');
  const [currentWedges, setCurrentWedges] = useState([]);
  const [selectedTokenInfo, setSelectedTokenInfo] = useState(null);
  const [generatedTokens, setGeneratedTokens] = useState([]);
  const [isSpinning, setIsSpinning] = useState(false);
  const [spinResult, setSpinResult] = useState(null); // To store result from /api/spin
  const [shouldContinue, setShouldContinue] = useState(true);
  const [step, setStep] = useState(0);
  const [inputPrompt, setInputPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectionMode, setSelectionMode] = useState('spin'); // 'spin' | 'manual'
  const [highlightedWedgeIndex, setHighlightedWedgeIndex] = useState(null);
  const [showTokenPop, setShowTokenPop] = useState(false);
  const [triggerPointerBounce, setTriggerPointerBounce] = useState(false);

  // Handle starting a new generation session
  const handleStart = async () => {
    if (!inputPrompt.trim()) {
      setError('Please enter a prompt');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await startGeneration(inputPrompt);

      // Calculate wedge angles from token probabilities
      const wedges = calculateWedgeAngles(response.tokens);

      setSessionId(response.session_id);
      setCurrentContext(response.context);
      setCurrentWedges(wedges);
      setStep(response.step);
      setShouldContinue(true);
      setGeneratedTokens([]);
    } catch (err) {
      setError(`Failed to start generation: ${err.message}`);
      console.error('Error starting generation:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle spinning the wheel by calling the backend to determine the result
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
      setError(`Failed to spin wheel: ${err.message}`);
      console.error('Error spinning wheel:', err);
      setIsSpinning(false); // Stop spinning on error
    }
  };

  // Handle when spin animation completes
  const handleSpinComplete = async () => {
    if (!spinResult) {
      console.error("Spin complete called without a spin result. This shouldn't happen.");
      setIsSpinning(false);
      return;
    }

    try {
      const { token: selected_token, token_id, probability, target_angle, is_other } = spinResult;

      // Find the wedge that contains this token
      // If the token came from "other", find the "Less Likely" wedge instead
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
      setError(`Failed to select token: ${err.message}`);
      console.error('Error selecting token:', err);
      setIsSpinning(false);
    }
  };

  // Handle manual wedge click
  const handleWedgeClick = async (wedge) => {
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
      setSelectedTokenInfo({
        token: response.selected_token,
        probability: wedge.probability,
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
      setError(`Failed to select token: ${err.message}`);
      console.error('Error selecting token:', err);
      setIsLoading(false);
    }
  };

  // Handle reset
  const handleReset = async () => {
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
    setInputPrompt('');
    setError(null);
    setSelectionMode('spin');
    setHighlightedWedgeIndex(null);
    setShowTokenPop(false);
    setTriggerPointerBounce(false);
  };

  // Handle mode toggle
  const handleModeToggle = (mode) => {
    setSelectionMode(mode);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">AI FUN Token Wheel</h1>
          <p className="mt-2 text-sm text-gray-600">
            Watch how language models generate text one token at a time
          </p>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8 w-full">
        {/* Error display */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
            <strong className="font-bold">Error: </strong>
            <span className="block sm:inline">{error}</span>
          </div>
        )}

        {/* Prompt input section */}
        {!sessionId && (
          <section className="section">
            <PromptInput
              value={inputPrompt}
              onChange={setInputPrompt}
              onStart={handleStart}
              isDisabled={isLoading}
            />
          </section>
        )}

        {/* Wheel and controls section */}
        {sessionId && currentWedges.length > 0 && (
          <>
            <section className="card mb-8">
              <TokenWheel
                wedges={currentWedges}
                selectedTokenInfo={selectedTokenInfo}
                isSpinning={isSpinning}
                targetAngle={spinResult?.target_angle}
                onSpinComplete={handleSpinComplete}
                selectionMode={selectionMode}
                onWedgeClick={handleWedgeClick}
                highlightedWedgeIndex={highlightedWedgeIndex}
                showTokenPop={showTokenPop}
                triggerPointerBounce={triggerPointerBounce}
              />

              <SpinControls
                onSpin={handleSpin}
                isDisabled={isSpinning || !shouldContinue}
                isSpinning={isSpinning}
                selectionMode={selectionMode}
                onModeToggle={handleModeToggle}
              />

              {!shouldContinue && (
                <div className="mt-6 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative" role="alert">
                  <strong className="font-bold">Complete! </strong>
                  <span className="block sm:inline">The model has stopped generating.</span>
                </div>
              )}
            </section>

            {/* Generated text section */}
            <section className="card mb-8">
              <GeneratedText context={currentContext} step={step} />
            </section>

            {/* Probability table section */}
            <section className="card mb-8">
              <TokenProbabilityTable
                wedges={currentWedges}
                selectedToken={generatedTokens[generatedTokens.length - 1]}
              />
            </section>

            {/* Reset button */}
            <section className="flex justify-center">
              <ResetButton onClick={handleReset} />
            </section>
          </>
        )}

        {/* Loading state */}
        {isLoading && (
          <div className="flex items-center justify-center">
            <div className="text-center">
              <svg className="animate-spin h-8 w-8 text-blue-500 mx-auto mb-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <p className="text-gray-600">Starting generation...</p>
            </div>
          </div>
        )}
      </main>

      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-600">
            Part of the AI Fundamentals course (CSI:1234) at the University of Iowa
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
