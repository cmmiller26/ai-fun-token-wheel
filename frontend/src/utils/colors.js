/**
 * Generate an array of distinct, colorblind-friendly colors
 * @param {number} count - Number of colors needed
 * @returns {Array<string>} Array of HSL color strings
 */
export const generateWedgeColors = (count) => {
  // Use a curated set of colorblind-friendly colors
  // Based on research for maximum distinction
  const baseColors = [
    'hsl(210, 80%, 60%)',   // Blue
    'hsl(30, 95%, 55%)',    // Orange
    'hsl(120, 60%, 50%)',   // Green
    'hsl(340, 85%, 55%)',   // Pink/Red
    'hsl(270, 70%, 60%)',   // Purple
    'hsl(180, 60%, 50%)',   // Cyan
    'hsl(60, 90%, 50%)',    // Yellow
    'hsl(0, 70%, 50%)',     // Red
    'hsl(150, 60%, 45%)',   // Teal
    'hsl(300, 65%, 55%)',   // Magenta
  ];

  // If we need more colors than our base set, generate additional ones
  if (count <= baseColors.length) {
    return baseColors.slice(0, count);
  }

  // Generate additional colors by varying saturation and lightness
  const colors = [...baseColors];
  for (let i = baseColors.length; i < count; i++) {
    const hue = (i * 360 / count) % 360;
    const saturation = 60 + (i % 3) * 10;
    const lightness = 50 + (i % 4) * 5;
    colors.push(`hsl(${hue}, ${saturation}%, ${lightness}%)`);
  }

  return colors;
};

/**
 * Get the special color/pattern for the "other" wedge
 * @returns {string} Color string for "other" wedge
 */
export const getOtherWedgeColor = () => {
  return 'hsl(0, 0%, 70%)'; // Gray color for "other" category
};

/**
 * Get the stroke color for wedge borders
 * @returns {string} Color string for borders
 */
export const getStrokeColor = () => {
  return '#ffffff';
};
