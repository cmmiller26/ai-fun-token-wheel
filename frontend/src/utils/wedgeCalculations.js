/**
 * Calculate wedge angles from token probabilities.
 * This logic mirrors the backend's `map_distribution_to_wedges` function to ensure
 * perfect consistency between the backend's target angle calculation and the
 * frontend's visual representation.
 *
 * @param {Array} tokens - Array of tokens with probabilities from the backend.
 * @returns {Array} Tokens with start_angle and end_angle added.
 */
export const calculateWedgeAngles = (tokens) => {
  let currentAngle = 0;

  return tokens.map((token, index) => {
    let wedgeAngle;

    // If this is the last token and it's the "other" wedge, make it fill the rest
    // of the circle. This corrects for any floating point inaccuracies and ensures
    // the visual representation perfectly matches the backend's angle calculations.
    if (index === tokens.length - 1 && token.is_other) {
      wedgeAngle = 360.0 - currentAngle;
    } else {
      wedgeAngle = token.probability * 360.0;
    }

    const wedge = {
      ...token,
      start_angle: currentAngle,
      end_angle: currentAngle + wedgeAngle,
    };
    currentAngle += wedgeAngle;
    return wedge;
  });
};
