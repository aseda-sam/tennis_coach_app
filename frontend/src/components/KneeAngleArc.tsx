import React from 'react';

interface KneeAngleArcProps {
  /** Knee flexion angle in degrees (typically 80–180). */
  angle: number;
}

/**
 * Draws a minimal two-line leg silhouette at the measured knee angle
 * with a small arc sweep showing the degrees. The "knee" joint sits
 * at the center; thigh goes up-right, shin goes down from there.
 *
 * 180° = fully straight leg. 90° = deep squat.
 */
const KneeAngleArc: React.FC<KneeAngleArcProps> = ({ angle }) => {
  const clampedAngle = Math.max(60, Math.min(180, angle));

  // Knee joint at center of the SVG
  const cx = 50;
  const cy = 52;
  const limbLen = 36;
  const arcRadius = 14;

  // Thigh goes up and to the right (fixed direction)
  // We orient it at roughly 35° from vertical
  const thighAngleRad = (-55 * Math.PI) / 180; // from positive X axis
  const thighX = cx + limbLen * Math.cos(thighAngleRad);
  const thighY = cy + limbLen * Math.sin(thighAngleRad);

  // Shin goes down. The angle between thigh and shin is the knee flexion.
  // Shin direction = thigh direction rotated by (180 - kneeAngle)
  // When kneeAngle=180, shin is straight continuation (opposite of thigh = straight leg)
  // When kneeAngle=90, shin is perpendicular
  const shinRotation = ((180 - clampedAngle) * Math.PI) / 180;
  // Thigh vector (knee to hip), reversed = knee to foot direction at 180°
  const straightX = Math.cos(thighAngleRad + Math.PI);
  const straightY = Math.sin(thighAngleRad + Math.PI);
  // Rotate the straight-leg direction by the bend amount (positive = bend inward)
  const shinDirX =
    straightX * Math.cos(shinRotation) - straightY * Math.sin(shinRotation);
  const shinDirY =
    straightX * Math.sin(shinRotation) + straightY * Math.cos(shinRotation);
  const shinX = cx + limbLen * shinDirX;
  const shinY = cy + limbLen * shinDirY;

  // Arc sweep: draw from thigh direction to shin direction
  // We need start/end angles for the arc (measured from positive X axis)
  const thighVecX = thighX - cx;
  const thighVecY = thighY - cy;
  const shinVecX = shinX - cx;
  const shinVecY = shinY - cy;

  const arcStartAngle = Math.atan2(thighVecY, thighVecX);
  const arcEndAngle = Math.atan2(shinVecY, shinVecX);

  const arcStartX = cx + arcRadius * Math.cos(arcStartAngle);
  const arcStartY = cy + arcRadius * Math.sin(arcStartAngle);
  const arcEndX = cx + arcRadius * Math.cos(arcEndAngle);
  const arcEndY = cy + arcRadius * Math.sin(arcEndAngle);

  // Determine sweep: we want the arc on the interior (smaller) side
  const largeArc = clampedAngle > 180 ? 1 : 0;
  // Sweep flag: going from thigh to shin clockwise (since thigh is upper-right, shin is lower)
  const sweepFlag = 1;

  return (
    <svg
      width="100%"
      viewBox="0 0 100 90"
      style={{ display: 'block' }}
      role="img"
      aria-label={`Knee angle: ${Math.round(angle)}°`}
    >
      {/* Thigh line */}
      <line
        x1={cx}
        y1={cy}
        x2={thighX}
        y2={thighY}
        stroke="var(--color-text-secondary)"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      {/* Shin line */}
      <line
        x1={cx}
        y1={cy}
        x2={shinX}
        y2={shinY}
        stroke="var(--color-text-secondary)"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      {/* Arc showing the angle */}
      <path
        d={`M ${arcStartX} ${arcStartY} A ${arcRadius} ${arcRadius} 0 ${largeArc} ${sweepFlag} ${arcEndX} ${arcEndY}`}
        fill="none"
        stroke="var(--color-arc)"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      {/* Knee joint dot */}
      <circle cx={cx} cy={cy} r="3" fill="var(--color-text-secondary)" />
    </svg>
  );
};

export default KneeAngleArc;
