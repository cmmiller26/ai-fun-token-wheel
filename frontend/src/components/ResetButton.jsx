import React from 'react';

const ResetButton = ({ onClick }) => {
  return (
    <button
      onClick={onClick}
      className="btn btn-danger"
      aria-label="Reset and start over"
    >
      Reset & Start Over
    </button>
  );
};

export default ResetButton;
