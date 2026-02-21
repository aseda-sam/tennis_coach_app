/**
 * Shared canvas drawing utilities used by VideoOverlay and StickFigureCanvas.
 *
 * Pure functions and constants only -- no React, no state, no side effects.
 */

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Skeleton bone connections (shared by both overlay and stick-figure views). */
export const SKELETON_CONNECTIONS = [
  // Arms
  ['left_shoulder', 'left_elbow'],
  ['left_elbow', 'left_wrist'],
  ['right_shoulder', 'right_elbow'],
  ['right_elbow', 'right_wrist'],
  // Legs
  ['left_hip', 'left_knee'],
  ['left_knee', 'left_ankle'],
  ['right_hip', 'right_knee'],
  ['right_knee', 'right_ankle'],
  // Torso frame
  ['left_shoulder', 'right_shoulder'],
  ['left_hip', 'right_hip'],
  ['left_shoulder', 'left_hip'],
  ['right_shoulder', 'right_hip'],
] as const;

/** Joint names rendered as circles in the stick-figure view. */
export const JOINT_POINTS = [
  'left_shoulder',
  'right_shoulder',
  'left_elbow',
  'right_elbow',
  'left_wrist',
  'right_wrist',
  'left_hip',
  'right_hip',
  'left_knee',
  'right_knee',
  'left_ankle',
  'right_ankle',
] as const;

export const OVERLAY_SKELETON_COLOR = '#00FF00';
export const STICK_FIGURE_SKELETON_COLOR = '#00ff88';
export const BALL_COLOR = '#FF1493';
export const BALL_TRAIL_LENGTH = 30; // ~1 second at 30fps

// ---------------------------------------------------------------------------
// Geometry helpers
// ---------------------------------------------------------------------------

export interface ContentRect {
  contentX: number;
  contentY: number;
  contentWidth: number;
  contentHeight: number;
  scaleX: number;
  scaleY: number;
}

/**
 * Compute the rendered video content rectangle accounting for object-fit.
 * Only handles 'contain' and 'cover' modes (the ones actually used).
 */
export function computeVideoContentRect(
  elementWidth: number,
  elementHeight: number,
  videoWidth: number,
  videoHeight: number,
  objectFit: 'contain' | 'cover'
): ContentRect {
  const elementAspect = elementWidth / elementHeight;
  const videoAspect = videoWidth / videoHeight;

  let contentX = 0;
  let contentY = 0;
  let contentWidth: number;
  let contentHeight: number;

  if (objectFit === 'contain') {
    if (videoAspect > elementAspect) {
      contentWidth = elementWidth;
      contentHeight = elementWidth / videoAspect;
      contentY = (elementHeight - contentHeight) / 2;
    } else {
      contentHeight = elementHeight;
      contentWidth = elementHeight * videoAspect;
      contentX = (elementWidth - contentWidth) / 2;
    }
  } else {
    // cover
    if (videoAspect > elementAspect) {
      contentHeight = elementHeight;
      contentWidth = elementHeight * videoAspect;
      contentX = (elementWidth - contentWidth) / 2;
    } else {
      contentWidth = elementWidth;
      contentHeight = elementWidth / videoAspect;
      contentY = (elementHeight - contentHeight) / 2;
    }
  }

  const scaleX = contentWidth / videoWidth;
  const scaleY = contentHeight / videoHeight;

  return { contentX, contentY, contentWidth, contentHeight, scaleX, scaleY };
}

/**
 * Rotate point coordinates for 90-degree clockwise rotation.
 * Used when overlay dimensions don't match video dimensions (phone rotation metadata issue).
 */
export function rotatePoint90(
  x: number,
  y: number,
  _width: number,
  height: number
): { x: number; y: number } {
  return { x: height - y, y: x };
}

/**
 * Normalize pose keypoints to a consistent scale and center position.
 * Returns coordinates in a normalized space where the figure is centered
 * and scaled based on torso length.
 */
export function normalizePose(
  keypoints: Record<string, number[]>,
  canvasWidth: number,
  canvasHeight: number
): Record<string, { x: number; y: number }> | null {
  const leftHip = keypoints['left_hip'];
  const rightHip = keypoints['right_hip'];
  const leftShoulder = keypoints['left_shoulder'];
  const rightShoulder = keypoints['right_shoulder'];

  if (!leftHip || !rightHip || !leftShoulder || !rightShoulder) {
    return null;
  }

  const hipCenterX = (leftHip[0] + rightHip[0]) / 2;
  const hipCenterY = (leftHip[1] + rightHip[1]) / 2;
  const shoulderCenterX = (leftShoulder[0] + rightShoulder[0]) / 2;
  const shoulderCenterY = (leftShoulder[1] + rightShoulder[1]) / 2;

  const torsoLength = Math.sqrt(
    Math.pow(shoulderCenterX - hipCenterX, 2) +
      Math.pow(shoulderCenterY - hipCenterY, 2)
  );

  if (torsoLength === 0) return null;

  const targetHeight = canvasHeight * 0.6;
  const scale = targetHeight / (torsoLength * 4);

  const centerX = canvasWidth / 2;
  const centerY = canvasHeight * 0.4;

  const normalized: Record<string, { x: number; y: number }> = {};

  for (const [name, coords] of Object.entries(keypoints)) {
    if (coords && coords.length >= 2) {
      const relX = coords[0] - hipCenterX;
      const relY = coords[1] - hipCenterY;
      normalized[name] = {
        x: centerX + relX * scale,
        y: centerY + relY * scale,
      };
    }
  }

  return normalized;
}

// ---------------------------------------------------------------------------
// VideoOverlay drawing helpers
// ---------------------------------------------------------------------------

export interface OverlaySkeletonParams {
  ctx: CanvasRenderingContext2D;
  keypoints: Record<string, number[]>;
  confidence: number;
  scaleX: number;
  scaleY: number;
  contentX: number;
  contentY: number;
  needsRotation: boolean;
  overlayWidth: number;
  overlayHeight: number;
}

/** Draw skeleton bones on the video overlay canvas. */
export function drawOverlaySkeleton(params: OverlaySkeletonParams): void {
  const {
    ctx,
    keypoints,
    confidence,
    scaleX,
    scaleY,
    contentX,
    contentY,
    needsRotation,
    overlayWidth,
    overlayHeight,
  } = params;

  ctx.strokeStyle = OVERLAY_SKELETON_COLOR;
  ctx.lineWidth = 2;
  ctx.shadowColor = '#000000';
  ctx.shadowBlur = 2;

  for (const [startKey, endKey] of SKELETON_CONNECTIONS) {
    const startPoint = keypoints[startKey];
    const endPoint = keypoints[endKey];

    if (
      startPoint &&
      endPoint &&
      startPoint.length >= 2 &&
      endPoint.length >= 2
    ) {
      let p1 = { x: startPoint[0], y: startPoint[1] };
      let p2 = { x: endPoint[0], y: endPoint[1] };

      if (needsRotation) {
        p1 = rotatePoint90(p1.x, p1.y, overlayWidth, overlayHeight);
        p2 = rotatePoint90(p2.x, p2.y, overlayWidth, overlayHeight);
      }

      const x1 = p1.x * scaleX + contentX;
      const y1 = p1.y * scaleY + contentY;
      const x2 = p2.x * scaleX + contentX;
      const y2 = p2.y * scaleY + contentY;

      if (confidence < 0.5) {
        ctx.setLineDash([5, 5]);
      } else {
        ctx.setLineDash([]);
      }

      ctx.strokeStyle = OVERLAY_SKELETON_COLOR;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }
  }
}

export interface OverlayBallParams {
  ctx: CanvasRenderingContext2D;
  ballPosition: number[] | undefined;
  trail: { x: number; y: number }[];
  scaleX: number;
  scaleY: number;
  contentX: number;
  contentY: number;
  contentWidth: number;
  contentHeight: number;
  needsRotation: boolean;
  overlayWidth: number;
  overlayHeight: number;
}

/**
 * Update the ball trail array and draw the trailing line + head dot.
 * Mutates `trail` in place (push / splice).
 */
export function drawOverlayBallTrail(params: OverlayBallParams): void {
  const {
    ctx,
    ballPosition,
    trail,
    scaleX,
    scaleY,
    contentX,
    contentY,
    contentWidth,
    contentHeight,
    needsRotation,
    overlayWidth,
    overlayHeight,
  } = params;

  if (ballPosition && ballPosition.length >= 2) {
    let ballP = { x: ballPosition[0], y: ballPosition[1] };
    if (needsRotation) {
      ballP = rotatePoint90(ballP.x, ballP.y, overlayWidth, overlayHeight);
    }
    const ballX = ballP.x * scaleX + contentX;
    const ballY = ballP.y * scaleY + contentY;
    trail.push({ x: ballX, y: ballY });
    if (trail.length > BALL_TRAIL_LENGTH) {
      trail.splice(0, trail.length - BALL_TRAIL_LENGTH);
    }
  }

  // Trailing line
  ctx.shadowBlur = 0;
  if (trail.length >= 2) {
    for (let i = 0; i < trail.length - 1; i++) {
      const t = (i + 1) / trail.length;
      const alpha = 0.1 + 0.8 * t;
      const lineWidth = 1 + 2 * t;
      ctx.strokeStyle = `rgba(255, 20, 147, ${alpha})`;
      ctx.lineWidth = lineWidth;
      ctx.beginPath();
      ctx.moveTo(trail[i].x, trail[i].y);
      ctx.lineTo(trail[i + 1].x, trail[i + 1].y);
      ctx.stroke();
    }
  }

  // Head dot
  if (trail.length >= 1) {
    const head = trail[trail.length - 1];
    const ballRadius = Math.max(6, (contentWidth + contentHeight) / 150);
    ctx.fillStyle = BALL_COLOR;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(head.x, head.y, ballRadius, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  }
}

// ---------------------------------------------------------------------------
// StickFigureCanvas drawing helpers
// ---------------------------------------------------------------------------

/** Draw a subtle grid background on the stick-figure canvas. */
export function drawGrid(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number
): void {
  ctx.fillStyle = '#1a1a2e';
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
  ctx.lineWidth = 1;
  const gridSize = 40;
  for (let x = 0; x < width; x += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let y = 0; y < height; y += gridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
}

/** Draw skeleton connections with glow effect on the stick-figure canvas. */
export function drawStickSkeleton(
  ctx: CanvasRenderingContext2D,
  normalizedPose: Record<string, { x: number; y: number }>,
  color: string
): void {
  ctx.shadowColor = color;
  ctx.shadowBlur = 8;
  ctx.strokeStyle = color;
  ctx.lineWidth = 3;
  ctx.lineCap = 'round';

  for (const [startKey, endKey] of SKELETON_CONNECTIONS) {
    const start = normalizedPose[startKey];
    const end = normalizedPose[endKey];

    if (start && end) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.stroke();
    }
  }
}

/** Draw white joint circles on key points. */
export function drawJoints(
  ctx: CanvasRenderingContext2D,
  normalizedPose: Record<string, { x: number; y: number }>
): void {
  ctx.shadowBlur = 4;
  ctx.fillStyle = '#ffffff';

  for (const jointName of JOINT_POINTS) {
    const joint = normalizedPose[jointName];
    if (joint) {
      ctx.beginPath();
      ctx.arc(joint.x, joint.y, 5, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  ctx.shadowBlur = 0;
}

/** Draw the ball trail line and head dot on the stick-figure canvas. */
export function drawStickBallTrail(
  ctx: CanvasRenderingContext2D,
  trail: { x: number; y: number }[]
): void {
  if (trail.length >= 2) {
    for (let i = 0; i < trail.length - 1; i++) {
      const t = (i + 1) / trail.length;
      const alpha = 0.1 + 0.8 * t;
      const lineWidth = 1 + 2 * t;
      ctx.strokeStyle = `rgba(255, 20, 147, ${alpha})`;
      ctx.lineWidth = lineWidth;
      ctx.beginPath();
      ctx.moveTo(trail[i].x, trail[i].y);
      ctx.lineTo(trail[i + 1].x, trail[i + 1].y);
      ctx.stroke();
    }
  }

  if (trail.length >= 1) {
    const head = trail[trail.length - 1];
    ctx.fillStyle = BALL_COLOR;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(head.x, head.y, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  }
}

export interface StickHudParams {
  ctx: CanvasRenderingContext2D;
  containerWidth: number;
  containerHeight: number;
  frameIndex: number;
  currentTime: number;
  confidence: number;
  phaseLabel?: string;
  phaseColor?: string;
}

/** Draw frame info, confidence indicator, and optional phase label. */
export function drawStickHud(params: StickHudParams): void {
  const {
    ctx,
    containerWidth,
    containerHeight,
    frameIndex,
    currentTime,
    confidence,
    phaseLabel,
    phaseColor,
  } = params;

  // Frame info
  ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
  ctx.font = '12px monospace';
  ctx.textAlign = 'left';
  ctx.fillText(`Frame: ${frameIndex}`, 10, containerHeight - 30);
  ctx.fillText(`Time: ${currentTime.toFixed(2)}s`, 10, containerHeight - 14);

  // Confidence indicator
  ctx.textAlign = 'right';
  ctx.fillStyle =
    confidence > 0.7 ? '#00ff88' : confidence > 0.4 ? '#ffaa00' : '#ff4444';
  ctx.fillText(
    `Confidence: ${(confidence * 100).toFixed(0)}%`,
    containerWidth - 10,
    containerHeight - 14
  );

  // Phase label
  if (phaseLabel) {
    const baseColor = phaseColor || STICK_FIGURE_SKELETON_COLOR;
    ctx.fillStyle = baseColor;
    ctx.font = 'bold 14px sans-serif';
    ctx.textAlign = 'left';
    ctx.shadowColor = 'rgba(0, 0, 0, 0.6)';
    ctx.shadowBlur = 4;
    ctx.fillText(phaseLabel, 12, 24);
    ctx.shadowBlur = 0;
  }
}
