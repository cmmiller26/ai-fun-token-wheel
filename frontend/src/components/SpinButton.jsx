import React from 'react';

const SpinButton = ({ onClick, isDisabled, isSpinning }) => {
  return (
    <button
      onClick={onClick}
      disabled={isDisabled}
      className="btn btn-spin"
      aria-label="Spin the probability wheel"
    >
      {isSpinning ? 'Spinning...' : 'Spin Wheel'}
    </button>
  );
};

export default SpinButton;
