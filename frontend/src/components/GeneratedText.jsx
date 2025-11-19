import React from 'react';

const GeneratedText = ({ context, step }) => {
  return (
    <div>
      <div className="flex justify-between items-baseline mb-3">
        <h2 className="text-xl font-semibold text-gray-800">Generated Text</h2>
        {step > 0 && (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold bg-indigo-100 text-indigo-800">
            Step: {step}
          </span>
        )}
      </div>
      <div className="bg-slate-50 rounded-lg p-6 min-h-36 max-h-96 overflow-y-auto border border-slate-200 shadow-inner">
        {context ? (
          <p className="text-slate-800 font-serif text-lg leading-relaxed whitespace-pre-wrap">
            {context}
          </p>
        ) : (
          <p className="text-slate-400 italic font-serif text-lg">
            The generated text will appear here once you start...
          </p>
        )}
      </div>
    </div>
  );
};

export default GeneratedText;
