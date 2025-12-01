import React, { useState } from 'react';
import PromptInput from './components/PromptInput';
import TokenWheel from './components/TokenWheel';
import SpinControls from './components/SpinControls';
import GeneratedText from './components/GeneratedText';
import ResetButton from './components/ResetButton';
import TokenProbabilityTable from './components/TokenProbabilityTable';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorMessage from './components/ErrorMessage';
import ModelSelector from './components/ModelSelector';
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

    // Model state
    availableModels,
    selectedModel,
    currentSessionModel,

    // Actions
    startGeneration,
    spin,
    handleSpinComplete,
    selectToken,
    resetGeneration,
    setSelectionMode,
    setSelectedModel,
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
          <section className="card">
            <ModelSelector
              models={availableModels}
              selectedModel={selectedModel}
              onModelChange={setSelectedModel}
              disabled={false}
            />
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
            {/* Current model indicator */}
            <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm font-medium text-gray-700">
                <span className="text-gray-600">Current Model:</span>{' '}
                <span className="text-blue-700 font-semibold">
                  {availableModels.find(m => m.key === currentSessionModel)?.name}
                </span>
                {' '}
                <span className="text-gray-500">
                  ({availableModels.find(m => m.key === currentSessionModel)?.params} parameters)
                </span>
              </p>
            </div>

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
          <div className="text-center">
            <p className="text-sm text-gray-600 mb-1">
              Part of the AI Fundamentals course (CSI:1040) at the University of Iowa
            </p>
            <p className="text-xs text-gray-500">
              Built with <a href="https://llama.meta.com" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Llama</a> •{' '}
              Powered by <a href="https://huggingface.co/gpt2" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">GPT-2</a> and{' '}
              <a href="https://huggingface.co/transformers" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Hugging Face Transformers</a>
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
