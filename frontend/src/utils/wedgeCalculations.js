/**
 * Calculate wedge angles from token probabilities
 * @param {Array} tokens - Array of tokens with probabilities
 * @returns {Array} Tokens with start_angle and end_angle added
 */
export const calculateWedgeAngles = (tokens) => {
  let currentAngle = 0;

  return tokens.map((token) => {
    const wedgeAngle = (token.probability / 1.0) * 360;
    const wedge = {
      ...token,
      start_angle: currentAngle,
      end_angle: currentAngle + wedgeAngle,
    };
    currentAngle += wedgeAngle;
    return wedge;
  });
};

/**
 * Find which token the landing angle corresponds to
 *
 * The pointer is fixed at the top (0° position). When the wheel rotates clockwise,
 * we need to find which wedge is now under the pointer.
 *
 * If the wheel rotates X degrees clockwise, the wedge that was at position (360 - X)
 * is now at the top (under the pointer at 0°).
 *
 * @param {number} landingAngle - How much the wheel rotated (0-360)
 * @param {Array} wedges - Array of wedges with start_angle and end_angle
 * @returns {Object} The token/wedge that was selected
 */
export const findTokenByAngle = (landingAngle, wedges) => {
  // Normalize rotation to 0-360 range
  const normalizedRotation = ((landingAngle % 360) + 360) % 360;

  // The pointer is at 0° (top). After rotating clockwise by landingAngle,
  // the wedge that's now at 0° was originally at (360 - landingAngle)
  // But since we want to know which wedge the pointer landed on after rotation,
  // we look at which wedge is at position (360 - normalizedRotation)
  const pointerAngle = (360 - normalizedRotation) % 360;

  console.log('Wheel rotated:', normalizedRotation.toFixed(1), '°');
  console.log('Pointer now points at wedge originally at:', pointerAngle.toFixed(1), '°');
  console.log('Wedges:', wedges.map(w => `${w.token}(${w.start_angle.toFixed(1)}-${w.end_angle.toFixed(1)})`));

  for (const wedge of wedges) {
    // Check if the pointer angle falls within this wedge
    if (pointerAngle >= wedge.start_angle && pointerAngle < wedge.end_angle) {
      console.log('✓ Selected wedge:', wedge.token, 'at', wedge.start_angle.toFixed(1), '-', wedge.end_angle.toFixed(1));
      return wedge;
    }
  }

  // Handle edge case: if pointerAngle is exactly 0, check first wedge
  if (Math.abs(pointerAngle) < 0.001) {
    const firstWedge = wedges[0];
    console.log('✓ Edge case (0°): Selected first wedge:', firstWedge.token);
    return firstWedge;
  }

  // Fallback: shouldn't happen, but return first wedge
  console.error(`❌ Could not find wedge for pointer angle ${pointerAngle.toFixed(1)}`);
  console.error('Available wedges:', wedges.map(w => ({
    token: w.token,
    start: w.start_angle,
    end: w.end_angle,
    prob: w.probability
  })));
  return wedges[0];
};
