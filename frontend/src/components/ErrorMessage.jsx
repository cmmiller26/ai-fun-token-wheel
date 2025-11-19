import React from 'react';

/**
 * ErrorMessage component
 * Displays an error message banner with dismiss functionality
 *
 * @param {Object} props
 * @param {string} props.message - Error message to display
 * @param {Function} props.onDismiss - Callback when dismiss button is clicked
 */
function ErrorMessage({ message, onDismiss }) {
  return (
    <div
      className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4 flex items-center justify-between"
      role="alert"
    >
      <div>
        <strong className="font-bold">Error: </strong>
        <span className="block sm:inline">{message}</span>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="text-red-700 hover:text-red-900 font-bold ml-4"
          aria-label="Dismiss error"
        >
          ✕
        </button>
      )}
    </div>
  );
}

export default ErrorMessage;
