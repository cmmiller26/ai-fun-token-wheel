import React, { useState } from 'react';
import PromptInput from './components/PromptInput';
import TokenWheel from './components/TokenWheel';
import SpinControls from './components/SpinControls';
import GeneratedText from './components/GeneratedText';
import ResetButton from './components/ResetButton';
import TokenProbabilityTable from './components/TokenProbabilityTable';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorMessage from './components/ErrorMessage';
import { useTokenWheel } from './hooks/useTokenWheel';

function App() {
  // Local UI state for prompt input
  const [inputPrompt, setInputPrompt] = useState('');

  // Use the custom hook for all business logic
  const {
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

    // Actions
    startGeneration,
    spin,
    handleSpinComplete,
    selectToken,
    resetGeneration,
    setSelectionMode,
    clearError,
  } = useTokenWheel();

  // Handle start button click
  const handleStart = async () => {
    await startGeneration(inputPrompt);
  };

  // Handle reset button click
  const handleReset = async () => {
    await resetGeneration();
    setInputPrompt(''); // Clear input field
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-slate-800 shadow-md">
        <div className="max-w-7xl mx-auto px-4 py-5 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-white tracking-tight">AI FUN Token Wheel</h1>
          <p className="mt-1 text-sm text-slate-300">
            A visualization of probabilistic token selection in language models.
          </p>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8 w-full">
        {/* Error display */}
        {error && <ErrorMessage message={error} onDismiss={clearError} />}

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

        {/* Main content section when generation is active */}
        {sessionId && currentWedges.length > 0 && (
          <>
            {/* Generated text section (now at the top) */}
            <section className="card mb-8">
              <GeneratedText context={currentContext} step={step} />
            </section>

            {/* Main interactive area: Wheel and Probabilities */}
            <div className="flex flex-col lg:flex-row gap-8">
              {/* Left side: Wheel and controls */}
              <section className="card lg:w-2/3">
                <TokenWheel
                  wedges={currentWedges}
                  selectedTokenInfo={selectedTokenInfo}
                  isSpinning={isSpinning}
                  targetAngle={spinResult?.target_angle}
                  onSpinComplete={handleSpinComplete}
                  selectionMode={selectionMode}
                  onWedgeClick={selectToken}
                  highlightedWedgeIndex={highlightedWedgeIndex}
                  showTokenPop={showTokenPop}
                  triggerPointerBounce={triggerPointerBounce}
                />

                <SpinControls
                  onSpin={spin}
                  isDisabled={isSpinning || !shouldContinue || isLoading}
                  isSpinning={isSpinning}
                  selectionMode={selectionMode}
                  onModeToggle={setSelectionMode}
                />

                {!shouldContinue && (
                  <div className="mt-6 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative" role="alert">
                    <strong className="font-bold">Complete! </strong>
                    <span className="block sm:inline">The model has stopped generating.</span>
                  </div>
                )}
              </section>

              {/* Right side: Probability legend */}
              <section className="card lg:w-1/3">
                <h2 className="text-xl font-semibold mb-4">Token Probabilities</h2>
                <TokenProbabilityTable
                  wedges={currentWedges}
                  selectedToken={generatedTokens[generatedTokens.length - 1]}
                />
              </section>
            </div>

            {/* Reset button */}
            <section className="flex justify-center mt-8">
              <ResetButton onClick={handleReset} />
            </section>
          </>
        )}

        {/* Loading state */}
        {isLoading && !sessionId && (
          <LoadingSpinner message="Starting generation..." />
        )}
      </main>

      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-600">
            Part of the AI Fundamentals course (CSI:1040) at the University of Iowa
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
