import React, { useState, useEffect, useRef } from 'react';
import { describeArc, calculateTextPosition } from '../utils/svgUtils';
import { generateWedgeColors, getOtherWedgeColor, getStrokeColor } from '../utils/colors';

const TokenWheel = ({ wedges, selectedTokenInfo, isSpinning, onSpinComplete, targetAngle = null, selectionMode = 'spin', onWedgeClick, highlightedWedgeIndex = null, showTokenPop = false, triggerPointerBounce = false }) => {
  const [rotation, setRotation] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const [hoveredWedge, setHoveredWedge] = useState(null);
  const [isResetting, setIsResetting] = useState(false);

  // SVG dimensions
  const size = 500;
  const centerX = size / 2;
  const centerY = size / 2;
  const radius = 200;
  const textRadius = radius * 0.65; // Position text at 65% of radius

  // Generate colors for wedges
  const wedgeColors = generateWedgeColors(wedges.length);

  // Use a ref to hold the onSpinComplete callback
  // This prevents the spinning effect from re-running when the parent component re-renders
  const onSpinCompleteRef = useRef(onSpinComplete);
  useEffect(() => {
    onSpinCompleteRef.current = onSpinComplete;
  });

  useEffect(() => {
    // Only spin if isSpinning is true and we have a targetAngle from the backend
    if (isSpinning && targetAngle !== null) {
      setIsAnimating(true);

      console.log('=== WHEEL SPIN DEBUG ===');
      console.log('Backend targetAngle:', targetAngle);
      console.log('Current rotation (raw):', rotation);

      // The backend provides the targetAngle where the selection is located within the wedge.
      // The pointer is at the top (0° position). To make the wedge appear under the pointer,
      // we rotate the wheel clockwise by targetAngle degrees.
      // Example: if target is at 90°, rotating the wheel 90° clockwise brings that position to the top.

      const minSpins = 10;
      const extraSpins = minSpins + Math.random() * 2;

      // Current normalized position of the wheel
      const currentRotation = rotation % 360;
      console.log('Current rotation (normalized):', currentRotation);

      // Target final rotation (where we want to end up) - simply the targetAngle
      const targetRotation = targetAngle;
      console.log('Target final rotation:', targetRotation);

      // Calculate shortest path to target, then add full spins
      let rotationDelta = targetRotation - currentRotation;
      console.log('Initial delta:', rotationDelta);

      // Ensure we always rotate forward (clockwise)
      if (rotationDelta <= 0) {
        rotationDelta += 360;
      }
      console.log('Forward delta:', rotationDelta);

      // Add the minimum number of full spins
      const totalRotation = (360 * extraSpins) + rotationDelta;
      console.log('Extra spins:', extraSpins, 'Total rotation to add:', totalRotation);
      console.log('Final rotation will be:', rotation + totalRotation);
      console.log('Final rotation (normalized):', (rotation + totalRotation) % 360);
      console.log('======================');

      setRotation(prevRotation => prevRotation + totalRotation);

      // After animation completes (4 seconds), notify parent
      const timer = setTimeout(() => {
        setIsAnimating(false);
        if (onSpinCompleteRef.current) {
          // No longer need to pass angle; parent already knows the result
          onSpinCompleteRef.current();
        }
      }, 4000);

      return () => clearTimeout(timer);
    }
  }, [isSpinning, targetAngle]);

  // Reset wheel to neutral position when wedges change (new token selected)
  useEffect(() => {
    if (!isSpinning && !isAnimating && highlightedWedgeIndex === null) {
      // Disable transition, normalize rotation, then re-enable transition
      setIsResetting(true);
      setRotation(prevRotation => prevRotation % 360);

      // Re-enable transitions after a brief moment
      const resetTimer = setTimeout(() => {
        setIsResetting(false);
      }, 50);

      return () => clearTimeout(resetTimer);
    }
  }, [wedges, isSpinning, isAnimating, highlightedWedgeIndex]);

  // Handle wedge click for manual selection
  const handleWedgeClick = (wedge) => {
    if (selectionMode === 'manual' && onWedgeClick && !isSpinning) {
      onWedgeClick(wedge);
    }
  };

  // Helper function to get color for a wedge
  const getWedgeColor = (wedge, index) => {
    if (wedge.is_other) {
      return '#9ca3af'; // Grey color for "Less Likely" wedge
    }
    return wedgeColors[index % wedgeColors.length];
  };

  // Helper function to determine if text should be shown in wedge
  const shouldShowText = (wedge) => {
    const wedgeAngle = wedge.end_angle - wedge.start_angle;
    return wedgeAngle >= 10; // Only show text if wedge is at least 10 degrees
  };

  // Helper function to format token text for display
  const formatTokenText = (token) => {
    // Replace special characters for better display
    return token.replace(/Ġ/g, ' ').replace(/Ċ/g, '\\n');
  };

  return (
    <div style={{ position: 'relative', width: `${size}px`, margin: '0 auto' }}>
      {/* CSS animations */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.6; }
          50% { opacity: 1; }
        }
        @keyframes bounce {
          0%, 100% { transform: translateX(-50%) translateY(0); }
          25% { transform: translateX(-50%) translateY(8px); }
          50% { transform: translateX(-50%) translateY(0); }
          75% { transform: translateX(-50%) translateY(4px); }
        }
        @keyframes tokenPop {
          0% { transform: translate(-50%, -50%) scale(0); opacity: 0; }
          30% { transform: translate(-50%, -50%) scale(1.1); opacity: 1; }
          70% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
          100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
        }
      `}</style>

      {/* Pointer/Arrow at top */}
      <div
        style={{
          position: 'absolute',
          top: '-20px',
          left: '50%',
          transform: 'translateX(-50%)',
          width: 0,
          height: 0,
          borderLeft: '15px solid transparent',
          borderRight: '15px solid transparent',
          borderTop: '25px solid #e74c3c',
          zIndex: 10,
          animation: triggerPointerBounce ? 'bounce 0.5s ease-out' : 'none',
          filter: triggerPointerBounce ? 'drop-shadow(0 0 8px rgba(231, 76, 60, 0.6))' : 'none',
        }}
      />

      {/* Spinning wheel */}
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{
          transform: `rotate(${rotation}deg)`,
          transition: (isAnimating && !isResetting) ? 'transform 4s cubic-bezier(0.15, 0.5, 0.2, 1)' : 'none',
          transformOrigin: 'center',
          filter: 'drop-shadow(0 4px 6px rgba(0, 0, 0, 0.1))',
        }}
      >
        {/* Render wedge shapes first */}
        {wedges.map((wedge, index) => {
          const path = describeArc(
            centerX,
            centerY,
            radius,
            wedge.start_angle,
            wedge.end_angle
          );

          const color = getWedgeColor(wedge, index);

          const isHovered = hoveredWedge === index;
          const isHighlighted = highlightedWedgeIndex === index;
          const isClickable = selectionMode === 'manual' && !isSpinning;

          return (
            <g key={`wedge-path-${index}`}>
              {/* Main wedge path */}
              <path
                d={path}
                fill={color}
                stroke={wedge.is_other ? '#6b7280' : getStrokeColor()}
                strokeWidth="2"
                strokeDasharray={wedge.is_other ? '4,4' : undefined}
                style={{
                  opacity: isHovered && isClickable ? 0.8 : (wedge.is_other ? 0.7 : 1),
                  cursor: isClickable ? 'pointer' : 'default',
                  transition: 'opacity 0.2s',
                  filter: isHighlighted ? 'brightness(1.2)' : 'none',
                }}
                onClick={() => handleWedgeClick(wedge)}
                onMouseEnter={() => isClickable && setHoveredWedge(index)}
                onMouseLeave={() => isClickable && setHoveredWedge(null)}
              />

              {/* Highlight glow effect */}
              {isHighlighted && (
                <path
                  d={path}
                  fill="none"
                  stroke="#fbbf24"
                  strokeWidth="6"
                  style={{
                    opacity: 0.8,
                    pointerEvents: 'none',
                    animation: 'pulse 1.5s ease-in-out infinite',
                  }}
                />
              )}
            </g>
          );
        })}

        {/* Render all text labels on top */}
        {wedges.map((wedge, index) => {
          const showText = shouldShowText(wedge);

          if (!showText) return null;

          return (
            <g key={`wedge-text-${index}`}>
              <text
                x={calculateTextPosition(centerX, centerY, textRadius, wedge.start_angle, wedge.end_angle).x}
                y={calculateTextPosition(centerX, centerY, textRadius, wedge.start_angle, wedge.end_angle).y}
                textAnchor="middle"
                dominantBaseline="middle"
                style={{
                  fontSize: '12px',
                  fontWeight: 'bold',
                  fill: '#000',
                  pointerEvents: 'none',
                }}
              >
                {formatTokenText(wedge.token)}
              </text>
              <text
                x={calculateTextPosition(centerX, centerY, textRadius * 0.8, wedge.start_angle, wedge.end_angle).x}
                y={calculateTextPosition(centerX, centerY, textRadius * 0.8, wedge.start_angle, wedge.end_angle).y + 15}
                textAnchor="middle"
                dominantBaseline="middle"
                style={{
                  fontSize: '10px',
                  fill: '#333',
                  pointerEvents: 'none',
                }}
              >
                {(wedge.probability * 100).toFixed(1)}%
              </text>
            </g>
          );
        })}

        {/* Center circle for aesthetics */}
        <circle
          cx={centerX}
          cy={centerY}
          r="30"
          fill="#ffffff"
          stroke="#333"
          strokeWidth="2"
        />
      </svg>

      {/* Token Pop Display */}
      {showTokenPop && selectedTokenInfo && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            background: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)',
            color: '#1f2937',
            padding: '20px 30px',
            borderRadius: '16px',
            boxShadow: '0 10px 40px rgba(0, 0, 0, 0.3)',
            zIndex: 20,
            animation: 'tokenPop 0.4s ease-out',
            border: '3px solid #ffffff',
            minWidth: '200px',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '14px', fontWeight: '600', marginBottom: '8px', opacity: 0.8 }}>
            Selected Token
          </div>
          <div style={{ fontSize: '32px', fontWeight: 'bold', marginBottom: '8px', wordBreak: 'break-word' }}>
            "{formatTokenText(selectedTokenInfo.token)}"
          </div>
          <div style={{ fontSize: '20px', fontWeight: '600' }}>
            {(selectedTokenInfo.probability * 100).toFixed(1)}%
          </div>
        </div>
      )}
    </div>
  );
};

export default TokenWheel;
