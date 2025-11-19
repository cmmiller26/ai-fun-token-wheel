import React from 'react';

const PromptInput = ({ value, onChange, onStart, isDisabled }) => {
  const handleSubmit = (e) => {
    e.preventDefault();
    if (value.trim() && !isDisabled) {
      onStart();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card max-w-2xl mx-auto">
      <div className="mb-4">
        <label htmlFor="prompt-input" className="block text-sm font-medium text-gray-700 mb-2">
          Enter your starting prompt:
        </label>
        <input
          id="prompt-input"
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={isDisabled}
          placeholder="Type your prompt here... (e.g., 'The cat sat on the')"
          className="input-text"
        />
        <p className="mt-2 text-xs text-gray-500">
          Start with a few words and watch the model generate text one token at a time
        </p>
      </div>
      <button
        type="submit"
        disabled={isDisabled || !value.trim()}
        className="btn btn-primary w-full"
      >
        Start Generation
      </button>
    </form>
  );
};

export default PromptInput;
