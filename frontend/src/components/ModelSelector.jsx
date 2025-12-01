import React from 'react';

/**
 * ModelSelector Component
 *
 * Displays a dropdown for selecting language models with metadata about each model.
 * Shows availability status and requirements for each model.
 *
 * @param {Array} models - List of model objects from API
 * @param {string} selectedModel - Currently selected model key
 * @param {function} onModelChange - Callback when model selection changes
 * @param {boolean} disabled - Whether the selector should be disabled
 */
const ModelSelector = ({ models, selectedModel, onModelChange, disabled }) => {
  const selected = models.find(m => m.key === selectedModel);

  return (
    <div className="mb-6">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Select Language Model
      </label>

      <select
        value={selectedModel || ''}
        onChange={(e) => onModelChange(e.target.value)}
        disabled={disabled}
        className={`block w-full px-4 py-3 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
          disabled ? 'bg-gray-100 cursor-not-allowed text-gray-500' : 'bg-white text-gray-900'
        }`}
      >
        {models.map(model => (
          <option key={model.key} value={model.key} disabled={!model.available}>
            {model.name} - {model.params} (~{model.ram_required_gb}GB RAM)
            {!model.available ? ' [Unavailable]' : ''}
          </option>
        ))}
      </select>

      {selected && (
        <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-md text-sm">
          <p className="text-gray-700">
            <strong>RAM Required:</strong> {selected.ram_required_gb}GB
          </p>
          {selected.requires_auth && !selected.available && (
            <p className="text-amber-700 mt-2">
              <strong>Note:</strong> This model requires instructor setup and is not available on this deployment.
            </p>
          )}
        </div>
      )}

      {disabled && (
        <p className="mt-2 text-sm text-gray-500 italic">
          Model locked during session. Reset to change.
        </p>
      )}
    </div>
  );
};

export default ModelSelector;
