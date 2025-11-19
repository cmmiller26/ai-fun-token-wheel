import React from 'react';
import { generateWedgeColors } from '../utils/colors';

const TokenProbabilityTable = ({ wedges, selectedToken }) => {
  // Sort wedges by probability (highest first) for the legend
  // But always put "Remaining Tokens" (is_other) at the end
  const sortedWedges = [...wedges].sort((a, b) => {
    // If one is "other" and one isn't, put "other" at the end
    if (a.is_other && !b.is_other) return 1;
    if (!a.is_other && b.is_other) return -1;
    // Otherwise sort by probability (highest first)
    return b.probability - a.probability;
  });

  // Generate the same colors used in the wheel
  const wedgeColors = generateWedgeColors(wedges.length);

  // Create a map of token to its original index to find the correct color
  const originalIndexMap = new Map(wedges.map((wedge, index) => [wedge.token, index]));

  // Format token for display
  const formatToken = (token) => {
    return token.replace(/Ġ/g, '␣').replace(/Ċ/g, '↵');
  };

  const getWedgeColor = (wedge) => {
    if (wedge.is_other) {
      return '#9ca3af'; // Grey for "Less Likely"
    }
    const originalIndex = originalIndexMap.get(wedge.token);
    return wedgeColors[originalIndex % wedgeColors.length];
  };

  return (
    <div className="flex flex-col h-full">
      {/* The title is now in App.jsx, so it's removed from here */}
      <div className="flex-grow overflow-y-auto pr-2" style={{ maxHeight: '450px' }}>
        <ul className="space-y-2">
          {sortedWedges.map((wedge) => {
            const isSelected = selectedToken === wedge.token;
            const percentage = (wedge.probability * 100).toFixed(1);

            return (
              <React.Fragment key={wedge.token}>
                <li
                  className={`flex items-center p-2 rounded-lg transition-all ${
                    isSelected ? 'bg-amber-100 shadow-sm' : ''
                  }`}
                >
                  <span
                    className="w-4 h-4 rounded-full mr-3 flex-shrink-0"
                    style={{ backgroundColor: getWedgeColor(wedge) }}
                  ></span>
                  <code className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">
                    {formatToken(wedge.token)}
                  </code>
                  <div className="flex-grow flex items-center justify-end ml-3">
                    <div className="w-full bg-gray-200 rounded-full h-2.5 mr-2">
                      <div
                        className="h-2.5 rounded-full"
                        style={{
                          width: `${Math.min(100, parseFloat(percentage))}%`,
                          backgroundColor: getWedgeColor(wedge),
                          transition: 'width 0.3s',
                        }}
                      ></div>
                    </div>
                    <span className="text-xs font-medium text-gray-600 w-10 text-right">
                      {percentage}%
                    </span>
                  </div>
                </li>
                {/* Show subcategory for "Remaining Tokens" if other_top_tokens exists */}
                {wedge.is_other && wedge.other_top_tokens && wedge.other_top_tokens.length > 0 && (
                  <li className="ml-8 space-y-1">
                    {wedge.other_top_tokens.map((topToken, idx) => {
                      const topPercentage = (topToken.probability * 100).toFixed(1);
                      return (
                        <div
                          key={`${topToken.token_id}-${idx}`}
                          className="flex items-center text-xs text-gray-600 py-1"
                        >
                          <span className="mr-2 text-gray-400">↳</span>
                          <code className="text-xs font-mono bg-gray-50 px-1.5 py-0.5 rounded">
                            {formatToken(topToken.token)}
                          </code>
                          <span className="ml-auto text-gray-500">
                            {topPercentage}%
                          </span>
                        </div>
                      );
                    })}
                    {/* Show "...and X more" if there are more tokens */}
                    {wedge.remaining_count && wedge.remaining_count > wedge.other_top_tokens.length && (
                      <div className="text-xs text-gray-400 italic pl-4 py-1">
                        ...and {(wedge.remaining_count - wedge.other_top_tokens.length).toLocaleString()} more
                      </div>
                    )}
                  </li>
                )}
              </React.Fragment>
            );
          })}
        </ul>
      </div>
    </div>
  );
};

export default TokenProbabilityTable;
