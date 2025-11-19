import React from 'react';

const SpinControls = ({
  onSpin,
  isDisabled,
  isSpinning,
  selectionMode,
  onModeToggle
}) => {
  return (
    <div className="flex flex-col items-center gap-4 mt-6">
      {/* Mode Toggle */}
      <div className="flex items-center gap-2 bg-gray-100 rounded-lg p-1">
        <button
          onClick={() => onModeToggle('spin')}
          className={`px-4 py-2 rounded-md font-medium transition-all ${
            selectionMode === 'spin'
              ? 'bg-white text-blue-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
          aria-label="Switch to spin mode"
        >
          Spin Mode
        </button>
        <button
          onClick={() => onModeToggle('manual')}
          className={`px-4 py-2 rounded-md font-medium transition-all ${
            selectionMode === 'manual'
              ? 'bg-white text-blue-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
          aria-label="Switch to manual selection mode"
        >
          Manual Selection
        </button>
      </div>

      {/* Mode Description */}
      <p className="text-sm text-gray-600 text-center max-w-md">
        {selectionMode === 'spin' ? (
          <span>
            Click <strong>Spin</strong> to randomly select the next token based on probabilities
          </span>
        ) : (
          <span>
            Click directly on a <strong>wedge</strong> to manually select the next token
          </span>
        )}
      </p>

      {/* Spin Button - Only shown in spin mode */}
      {selectionMode === 'spin' && (
        <button
          onClick={onSpin}
          disabled={isDisabled}
          className="btn btn-primary text-lg px-8 py-4 shadow-lg hover:shadow-xl transform hover:scale-105 disabled:transform-none disabled:shadow-md"
          aria-label="Spin the probability wheel"
        >
          {isSpinning ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Spinning...
            </span>
          ) : (
            'Spin Wheel'
          )}
        </button>
      )}
    </div>
  );
};

export default SpinControls;
