import React from 'react';

const TokenProbabilityTable = ({ wedges, selectedToken }) => {
  // Sort wedges by probability (highest first)
  const sortedWedges = [...wedges].sort((a, b) => b.probability - a.probability);

  // Format token for display
  const formatToken = (token) => {
    return token.replace(/Ġ/g, '␣').replace(/Ċ/g, '↵');
  };

  return (
    <div>
      <h3 className="text-xl font-semibold text-gray-900 mb-4">Token Probabilities</h3>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Token
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Probability
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Percentage
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedWedges.map((wedge, index) => (
              <tr
                key={`prob-${index}`}
                className={`${
                  selectedToken === wedge.token ? 'bg-blue-50' : 'hover:bg-gray-50'
                } transition-colors`}
              >
                <td className="px-4 py-3 whitespace-nowrap">
                  <code className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">
                    {formatToken(wedge.token)}
                  </code>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                  {wedge.probability.toFixed(4)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-gray-200 rounded-full h-4 max-w-xs overflow-hidden">
                      <div
                        className="bg-blue-500 h-full rounded-full transition-all duration-300"
                        style={{ width: `${wedge.probability * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium text-gray-700 min-w-[3rem] text-right">
                      {(wedge.probability * 100).toFixed(1)}%
                    </span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TokenProbabilityTable;
