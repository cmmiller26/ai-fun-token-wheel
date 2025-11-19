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
        {isLoading && !sessionId && (
          <LoadingSpinner message="Starting generation..." />
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
