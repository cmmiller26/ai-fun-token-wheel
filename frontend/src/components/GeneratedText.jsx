import React from 'react';

const GeneratedText = ({ context, step }) => {
  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-semibold text-gray-900">Generated Text</h3>
        {step > 0 && (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
            Step {step}
          </span>
        )}
      </div>
      <div className="bg-gray-50 rounded-lg p-4 min-h-32 max-h-96 overflow-y-auto border border-gray-200">
        {context ? (
          <p className="text-gray-900 font-mono text-sm leading-relaxed whitespace-pre-wrap">{context}</p>
        ) : (
          <p className="text-gray-400 italic">Generated text will appear here...</p>
        )}
      </div>
    </div>
  );
};

export default GeneratedText;
