/**
 * Convert polar coordinates to cartesian coordinates
 * @param {number} centerX - Center X coordinate
 * @param {number} centerY - Center Y coordinate
 * @param {number} radius - Radius
 * @param {number} angleInDegrees - Angle in degrees (0° = right, 90° = down in SVG)
 * @returns {object} {x, y} coordinates
 */
export const polarToCartesian = (centerX, centerY, radius, angleInDegrees) => {
  const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180.0;
  return {
    x: centerX + radius * Math.cos(angleInRadians),
    y: centerY + radius * Math.sin(angleInRadians),
  };
};

/**
 * Generate SVG arc path for a wedge
 * @param {number} x - Center X
 * @param {number} y - Center Y
 * @param {number} radius - Radius
 * @param {number} startAngle - Start angle in degrees
 * @param {number} endAngle - End angle in degrees
 * @returns {string} SVG path string
 */
export const describeArc = (x, y, radius, startAngle, endAngle) => {
  const angleSpan = endAngle - startAngle;

  // Special case: for a full circle (or nearly full), draw a complete circle
  if (angleSpan >= 359.99) {
    return `M ${x} ${y} m ${-radius}, 0 a ${radius},${radius} 0 1,0 ${radius * 2},0 a ${radius},${radius} 0 1,0 ${-radius * 2},0`;
  }

  const start = polarToCartesian(x, y, radius, endAngle);
  const end = polarToCartesian(x, y, radius, startAngle);

  // Determine if we need the large arc flag (for arcs > 180°)
  const largeArcFlag = angleSpan <= 180 ? '0' : '1';

  const d = [
    'M', x, y,                    // Move to center
    'L', start.x, start.y,        // Line to arc start
    'A', radius, radius, 0, largeArcFlag, 0, end.x, end.y,  // Arc
    'Z'                           // Close path back to center
  ].join(' ');

  return d;
};

/**
 * Calculate text position in the middle of a wedge
 * @param {number} centerX - Center X
 * @param {number} centerY - Center Y
 * @param {number} radius - Radius for text placement (usually 60-70% of wedge radius)
 * @param {number} startAngle - Start angle in degrees
 * @param {number} endAngle - End angle in degrees
 * @returns {object} {x, y, angle} for text positioning
 */
export const calculateTextPosition = (centerX, centerY, radius, startAngle, endAngle) => {
  const midAngle = (startAngle + endAngle) / 2;
  const position = polarToCartesian(centerX, centerY, radius, midAngle);

  return {
    x: position.x,
    y: position.y,
    angle: midAngle,
  };
};
