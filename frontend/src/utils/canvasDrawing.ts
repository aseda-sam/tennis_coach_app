/**
 * Shared canvas drawing utilities used by StickFigureCanvas.
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
export const SKELETON_COLOR = '#4AD090'; // Desaturated analytical green
export const GROUND_PLANE_COLOR = '#6B7A8D'; // Neutral cool blue-grey
export const BALL_COLOR = '#C4D93B'; // Tennis ball yellow-green
export const BALL_TRAIL_LENGTH = 30; // ~1 second at 30fps
export const ANNOTATION_COLOR = '#00D4FF';

/** Per-bone thickness — keyed by "startKey:endKey". */
export const BONE_THICKNESS: Record<string, number> = {
  // Torso frame
  'left_shoulder:right_shoulder': 4,
  'right_shoulder:left_shoulder': 4,
  'left_hip:right_hip': 4,
  'right_hip:left_hip': 4,
  'left_shoulder:left_hip': 4,
  'right_shoulder:right_hip': 4,
  // Upper arms
  'left_shoulder:left_elbow': 2.5,
  'right_shoulder:right_elbow': 2.5,
  // Lower arms
  'left_elbow:left_wrist': 2,
  'right_elbow:right_wrist': 2,
  // Upper legs
  'left_hip:left_knee': 3,
  'right_hip:right_knee': 3,
  // Lower legs
  'left_knee:left_ankle': 2.5,
  'right_knee:right_ankle': 2.5,
};

/** Joints that get the ring effect (shoulder + hip pivots). */
export const MAJOR_JOINTS = new Set([
  'left_shoulder',
  'right_shoulder',
  'left_hip',
  'right_hip',
]);

export const JOINT_RADIUS_MAJOR = 3;
export const JOINT_RADIUS_MINOR = 1.8;
export const HEAD_OFFSET_RATIO = 0.35;
export const HEAD_RADIUS = 6;
export const GROUND_PLANE_GLOW_BLUR = 6;
export const GROUND_PLANE_Y_OFFSET = 12;
export const SKELETON_GLOW_BLUR = 3;
export const STICK_BALL_HEAD_RADIUS = 7;
export const STICK_BALL_HEAD_GLOW_BLUR = 6;
export const ANNOTATION_Y_MARGIN = 18;

// Adaptive scale layout constants
export const SCENE_TOP_MARGIN = 0.05; // 5% padding above highest point
export const SCENE_BOTTOM_MARGIN = 0.08; // 8% padding below ground
export const MIN_EXTENT_TORSOS = 4; // Floor on scene extent (prevents absurdly large figure)

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
// Fixed reference-frame normalization
// ---------------------------------------------------------------------------

/** Reference values computed once from a stable frame (video pixel space). */
export interface NormalizationRef {
  hipCenterX: number; // video pixel coords
  hipCenterY: number; // video pixel coords
  torsoLength: number; // video pixel distance
  groundY: number; // video pixel Y of lowest ankle in ref frame
  topY: number; // video pixel Y of highest point (ball peak or head estimate)
}

/**
 * Compute a fixed normalization reference from the frame at `serveStartTime`.
 * Skips frames with missing core keypoints (shoulders + hips) and tries the
 * next frames. Returns `null` when no valid frame is found.
 *
 * Also scans all frames for the highest ball position to compute `topY`,
 * ensuring the full toss arc fits on canvas.
 */
export function computeNormalizationRef(
  frames: { keypoints: Record<string, number[]>; ball_position?: number[] }[],
  serveStartTime: number | undefined,
  fps: number
): NormalizationRef | null {
  if (!frames || frames.length === 0) return null;

  let startIdx = 0;
  if (serveStartTime != null && fps > 0) {
    startIdx = Math.round(serveStartTime * fps);
  }
  startIdx = Math.max(0, Math.min(startIdx, frames.length - 1));

  const maxAttempts = Math.min(10, frames.length);
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const idx = Math.min(startIdx + attempt, frames.length - 1);
    const frame = frames[idx];
    if (!frame?.keypoints) continue;

    const ls = frame.keypoints['left_shoulder'];
    const rs = frame.keypoints['right_shoulder'];
    const lh = frame.keypoints['left_hip'];
    const rh = frame.keypoints['right_hip'];

    if (!ls || !rs || !lh || !rh) continue;

    const hipCenterX = (lh[0] + rh[0]) / 2;
    const hipCenterY = (lh[1] + rh[1]) / 2;
    const shoulderCenterX = (ls[0] + rs[0]) / 2;
    const shoulderCenterY = (ls[1] + rs[1]) / 2;

    const torsoLength = Math.sqrt(
      (shoulderCenterX - hipCenterX) ** 2 + (shoulderCenterY - hipCenterY) ** 2
    );

    if (torsoLength === 0) continue;

    // Ground Y from ankles, falling back to hip + 2*torso
    const la = frame.keypoints['left_ankle'];
    const ra = frame.keypoints['right_ankle'];
    let groundY: number;
    if (la || ra) {
      groundY = Math.max(la?.[1] ?? 0, ra?.[1] ?? 0);
    } else {
      groundY = hipCenterY + torsoLength * 2;
    }

    // Scan all frames for the highest ball position (min Y in video coords)
    let minBallY = Infinity;
    for (const f of frames) {
      if (f.ball_position && f.ball_position.length >= 2) {
        minBallY = Math.min(minBallY, f.ball_position[1]);
      }
    }

    // Head estimate: top of head circle above shoulder center
    const headEstimate =
      shoulderCenterY -
      torsoLength * (HEAD_OFFSET_RATIO + HEAD_RADIUS / torsoLength);

    // topY = highest point we need to render
    let topY = headEstimate;
    if (minBallY !== Infinity) {
      topY = Math.min(topY, minBallY);
    }

    // Sanity cap: don't let topY be more than 8 torso lengths above hips
    topY = Math.max(topY, hipCenterY - torsoLength * 8);

    return { hipCenterX, hipCenterY, torsoLength, groundY, topY };
  }

  return null;
}

/**
 * Normalize pose using a fixed reference frame's scale and position anchor.
 * Same output shape as `normalizePose` but stable across frames.
 * Does not require the frame's own hips/shoulders — any keypoints work.
 *
 * Scale is computed from the full vertical extent (groundY - topY) so that
 * the ball toss arc and ground both fit on canvas.
 */
export function normalizePoseFixed(
  keypoints: Record<string, number[]>,
  canvasWidth: number,
  canvasHeight: number,
  ref: NormalizationRef
): Record<string, { x: number; y: number }> {
  const usableHeight =
    canvasHeight * (1 - SCENE_TOP_MARGIN - SCENE_BOTTOM_MARGIN);
  const groundCanvasY = canvasHeight * (1 - SCENE_BOTTOM_MARGIN);
  const extent = Math.max(
    ref.groundY - ref.topY,
    ref.torsoLength * MIN_EXTENT_TORSOS
  );
  const scale = usableHeight / extent;

  const canvasAnchorX = canvasWidth / 2;
  const canvasAnchorY = groundCanvasY - (ref.groundY - ref.hipCenterY) * scale;

  const normalized: Record<string, { x: number; y: number }> = {};

  for (const [name, coords] of Object.entries(keypoints)) {
    if (coords && coords.length >= 2) {
      const relX = coords[0] - ref.hipCenterX;
      const relY = coords[1] - ref.hipCenterY;
      normalized[name] = {
        x: canvasAnchorX + relX * scale,
        y: canvasAnchorY + relY * scale,
      };
    }
  }

  return normalized;
}

/**
 * Draw a fixed ground plane using the reference frame's ground Y.
 * Same gradient + glow rendering as `drawGroundPlane`.
 */
export function drawGroundPlaneFixed(
  ctx: CanvasRenderingContext2D,
  canvasWidth: number,
  canvasHeight: number,
  ref: NormalizationRef
): void {
  const groundCanvasY = canvasHeight * (1 - SCENE_BOTTOM_MARGIN);
  const groundY = groundCanvasY + GROUND_PLANE_Y_OFFSET;

  const figureCenterX = canvasWidth / 2;
  const lineWidth = canvasWidth * 0.6;
  const startX = figureCenterX - lineWidth / 2;
  const endX = figureCenterX + lineWidth / 2;

  const color = GROUND_PLANE_COLOR;

  // Gradient: transparent → color → transparent
  const grad = ctx.createLinearGradient(startX, groundY, endX, groundY);
  grad.addColorStop(0, 'rgba(0, 0, 0, 0)');
  grad.addColorStop(0.3, color);
  grad.addColorStop(0.7, color);
  grad.addColorStop(1, 'rgba(0, 0, 0, 0)');

  // Pass 1: glow halo
  ctx.save();
  ctx.globalAlpha = 0.4;
  ctx.strokeStyle = grad;
  ctx.lineWidth = 1.5;
  ctx.shadowColor = color;
  ctx.shadowBlur = GROUND_PLANE_GLOW_BLUR;
  ctx.beginPath();
  ctx.moveTo(startX, groundY);
  ctx.lineTo(endX, groundY);
  ctx.stroke();
  ctx.restore();

  // Pass 2: crisp center line
  ctx.save();
  ctx.globalAlpha = 0.4;
  ctx.strokeStyle = grad;
  ctx.lineWidth = 1;
  ctx.shadowBlur = 0;
  ctx.beginPath();
  ctx.moveTo(startX, groundY);
  ctx.lineTo(endX, groundY);
  ctx.stroke();
  ctx.restore();
}

// ---------------------------------------------------------------------------
// Overlay drawing helpers
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
      ctx.strokeStyle = `rgba(196, 217, 59, ${alpha})`;
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

/** Draw skeleton connections with glow effect and variable bone thickness. */
export function drawStickSkeleton(
  ctx: CanvasRenderingContext2D,
  normalizedPose: Record<string, { x: number; y: number }>,
  color: string
): void {
  ctx.shadowColor = color;
  ctx.shadowBlur = SKELETON_GLOW_BLUR;
  ctx.strokeStyle = color;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  for (const [startKey, endKey] of SKELETON_CONNECTIONS) {
    const start = normalizedPose[startKey];
    const end = normalizedPose[endKey];

    if (start && end) {
      ctx.lineWidth = BONE_THICKNESS[`${startKey}:${endKey}`] ?? 3;
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.stroke();
    }
  }
}

/**
 * Convert a hex color to an rgba string.
 * Accepts "#RRGGBB" or "#RGB" format.
 */
function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace('#', '');
  const r = parseInt(h.length === 3 ? h[0] + h[0] : h.substring(0, 2), 16);
  const g = parseInt(h.length === 3 ? h[1] + h[1] : h.substring(2, 4), 16);
  const b = parseInt(h.length === 3 ? h[2] + h[2] : h.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/** Draw differentiated joints: stroked rings for major pivots, dots for minor. */
export function drawJoints(
  ctx: CanvasRenderingContext2D,
  normalizedPose: Record<string, { x: number; y: number }>,
  color: string
): void {
  ctx.shadowBlur = 0;

  for (const jointName of JOINT_POINTS) {
    const joint = normalizedPose[jointName];
    if (!joint) continue;

    if (MAJOR_JOINTS.has(jointName)) {
      // Major joints: color-matched ring at 50% opacity + faint white fill
      ctx.fillStyle = 'rgba(255, 255, 255, 0.08)';
      ctx.beginPath();
      ctx.arc(joint.x, joint.y, JOINT_RADIUS_MAJOR, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = hexToRgba(color, 0.5);
      ctx.lineWidth = 1.5;
      ctx.stroke();
    } else {
      // Minor joints: color-matched dot at 40% opacity
      ctx.fillStyle = hexToRgba(color, 0.4);
      ctx.beginPath();
      ctx.arc(joint.x, joint.y, JOINT_RADIUS_MINOR, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

/** Draw a head hint circle above the shoulder midpoint. */
export function drawHead(
  ctx: CanvasRenderingContext2D,
  normalizedPose: Record<string, { x: number; y: number }>,
  color: string
): void {
  const ls = normalizedPose['left_shoulder'];
  const rs = normalizedPose['right_shoulder'];
  const lh = normalizedPose['left_hip'];
  const rh = normalizedPose['right_hip'];
  if (!ls || !rs || !lh || !rh) return;

  const shoulderMidX = (ls.x + rs.x) / 2;
  const shoulderMidY = (ls.y + rs.y) / 2;
  const hipMidX = (lh.x + rh.x) / 2;
  const hipMidY = (lh.y + rh.y) / 2;
  const torsoLength = Math.sqrt(
    (shoulderMidX - hipMidX) ** 2 + (shoulderMidY - hipMidY) ** 2
  );
  if (torsoLength === 0) return;

  // Direction from hip to shoulder (up the torso)
  const dx = (shoulderMidX - hipMidX) / torsoLength;
  const dy = (shoulderMidY - hipMidY) / torsoLength;

  const headCenterX = shoulderMidX + dx * torsoLength * HEAD_OFFSET_RATIO;
  const headCenterY = shoulderMidY + dy * torsoLength * HEAD_OFFSET_RATIO;

  // Neck line
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.shadowColor = color;
  ctx.shadowBlur = SKELETON_GLOW_BLUR;
  ctx.beginPath();
  ctx.moveTo(shoulderMidX, shoulderMidY);
  ctx.lineTo(headCenterX, headCenterY);
  ctx.stroke();

  // Head circle (ring, not filled)
  ctx.beginPath();
  ctx.arc(headCenterX, headCenterY, HEAD_RADIUS, 0, Math.PI * 2);
  ctx.stroke();

  ctx.shadowBlur = 0;
}

/** Draw a glowing ground plane line beneath the figure. */
export function drawGroundPlane(
  ctx: CanvasRenderingContext2D,
  normalizedPose: Record<string, { x: number; y: number }>,
  canvasWidth: number
): void {
  const la = normalizedPose['left_ankle'];
  const ra = normalizedPose['right_ankle'];
  if (!la && !ra) return;

  const lowestY = Math.max(la?.y ?? 0, ra?.y ?? 0);
  const groundY = lowestY + GROUND_PLANE_Y_OFFSET;

  // Center on the figure, ~60% canvas width
  const figureCenterX = ((la?.x ?? 0) + (ra?.x ?? 0)) / (la && ra ? 2 : 1);
  const lineWidth = canvasWidth * 0.6;
  const startX = figureCenterX - lineWidth / 2;
  const endX = figureCenterX + lineWidth / 2;

  const color = GROUND_PLANE_COLOR;

  // Gradient: transparent → color → transparent
  const grad = ctx.createLinearGradient(startX, groundY, endX, groundY);
  grad.addColorStop(0, 'rgba(0, 0, 0, 0)');
  grad.addColorStop(0.3, color);
  grad.addColorStop(0.7, color);
  grad.addColorStop(1, 'rgba(0, 0, 0, 0)');

  // Pass 1: glow halo
  ctx.save();
  ctx.globalAlpha = 0.4;
  ctx.strokeStyle = grad;
  ctx.lineWidth = 1.5;
  ctx.shadowColor = color;
  ctx.shadowBlur = GROUND_PLANE_GLOW_BLUR;
  ctx.beginPath();
  ctx.moveTo(startX, groundY);
  ctx.lineTo(endX, groundY);
  ctx.stroke();
  ctx.restore();

  // Pass 2: crisp center line
  ctx.save();
  ctx.globalAlpha = 0.4;
  ctx.strokeStyle = grad;
  ctx.lineWidth = 1;
  ctx.shadowBlur = 0;
  ctx.beginPath();
  ctx.moveTo(startX, groundY);
  ctx.lineTo(endX, groundY);
  ctx.stroke();
  ctx.restore();
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
      ctx.strokeStyle = `rgba(196, 217, 59, ${alpha})`;
      ctx.lineWidth = lineWidth;
      ctx.beginPath();
      ctx.moveTo(trail[i].x, trail[i].y);
      ctx.lineTo(trail[i + 1].x, trail[i + 1].y);
      ctx.stroke();
    }
  }

  if (trail.length >= 1) {
    const head = trail[trail.length - 1];
    ctx.shadowColor = BALL_COLOR;
    ctx.shadowBlur = STICK_BALL_HEAD_GLOW_BLUR;
    ctx.fillStyle = BALL_COLOR;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(head.x, head.y, STICK_BALL_HEAD_RADIUS, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.shadowBlur = 0;
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

/** Draw frame info and optional phase label in a pill. */
export function drawStickHud(params: StickHudParams): void {
  const {
    ctx,
    containerHeight,
    frameIndex,
    currentTime,
    phaseLabel,
    phaseColor,
  } = params;

  // Frame info — bottom left
  ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
  ctx.font = '11px monospace';
  ctx.textAlign = 'left';
  ctx.fillText(
    `F${frameIndex}  ${currentTime.toFixed(2)}s`,
    10,
    containerHeight - 12
  );

  // Phase label pill — top left
  if (phaseLabel) {
    const baseColor = phaseColor || SKELETON_COLOR;
    ctx.font = 'bold 13px sans-serif';
    const textWidth = ctx.measureText(phaseLabel).width;
    const pillPadX = 10;
    const pillPadY = 6;
    const pillX = 10;
    const pillY = 10;
    const pillW = textWidth + pillPadX * 2;
    const pillH = 13 + pillPadY * 2;
    const pillR = pillH / 2;

    // Pill background
    ctx.fillStyle = baseColor;
    ctx.globalAlpha = 0.2;
    ctx.beginPath();
    ctx.moveTo(pillX + pillR, pillY);
    ctx.lineTo(pillX + pillW - pillR, pillY);
    ctx.arcTo(pillX + pillW, pillY, pillX + pillW, pillY + pillR, pillR);
    ctx.arcTo(
      pillX + pillW,
      pillY + pillH,
      pillX + pillW - pillR,
      pillY + pillH,
      pillR
    );
    ctx.lineTo(pillX + pillR, pillY + pillH);
    ctx.arcTo(pillX, pillY + pillH, pillX, pillY + pillH - pillR, pillR);
    ctx.arcTo(pillX, pillY, pillX + pillR, pillY, pillR);
    ctx.closePath();
    ctx.fill();
    ctx.globalAlpha = 1;

    // Pill text
    ctx.fillStyle = baseColor;
    ctx.textAlign = 'left';
    ctx.fillText(phaseLabel, pillX + pillPadX, pillY + pillPadY + 11);
  }
}

// ---------------------------------------------------------------------------
// Metric annotation helpers (stick-figure mode only)
// ---------------------------------------------------------------------------

/**
 * Compute fade opacity based on proximity to annotation timestamp.
 * Returns 0 when outside the window, 1 at the exact timestamp.
 */
export function computeAnnotationOpacity(
  currentTime: number,
  annotationTime: number,
  windowMs: number = 300
): number {
  const windowSec = windowMs / 1000;
  const dist = Math.abs(currentTime - annotationTime);
  if (dist > windowSec) return 0;
  return 1 - dist / windowSec;
}

export interface TossHeightAnnotationParams {
  ctx: CanvasRenderingContext2D;
  ballY: number;
  shoulderY: number;
  canvasWidth: number;
  canvasHeight: number;
  value: number;
  opacity: number;
}

/**
 * Draw toss height annotation: horizontal dashed line at ball peak Y with glow,
 * vertical measurement bracket from shoulder to ball, rounded-rect label backdrop,
 * and "Peak Height" sub-label. Ball Y is clamped to canvas bounds.
 */
export function drawTossHeightAnnotation(
  params: TossHeightAnnotationParams
): void {
  const { ctx, shoulderY, canvasWidth, canvasHeight, value, opacity } = params;

  // Clamp ballY to canvas bounds
  const ballY = Math.max(
    ANNOTATION_Y_MARGIN,
    Math.min(params.ballY, canvasHeight - ANNOTATION_Y_MARGIN)
  );

  ctx.save();
  ctx.globalAlpha = opacity;

  // Shortened horizontal dashed line (~120px) centered on bracket
  const bracketX = canvasWidth - 40;
  const dashHalfWidth = 60;
  ctx.shadowColor = ANNOTATION_COLOR;
  ctx.shadowBlur = 6;
  ctx.strokeStyle = ANNOTATION_COLOR;
  ctx.lineWidth = 1;
  ctx.setLineDash([6, 4]);
  ctx.beginPath();
  ctx.moveTo(Math.max(0, bracketX - dashHalfWidth), ballY);
  ctx.lineTo(Math.min(canvasWidth, bracketX + dashHalfWidth), ballY);
  ctx.stroke();
  ctx.shadowBlur = 0;

  // Vertical bracket from shoulder to ball
  ctx.setLineDash([]);
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.moveTo(bracketX, shoulderY);
  ctx.lineTo(bracketX, ballY);
  ctx.stroke();

  // Bracket caps (bolder)
  const capWidth = 10;
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.moveTo(bracketX - capWidth, shoulderY);
  ctx.lineTo(bracketX + capWidth, shoulderY);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(bracketX - capWidth, ballY);
  ctx.lineTo(bracketX + capWidth, ballY);
  ctx.stroke();

  // Value label with rounded-rect backdrop
  const midY = (shoulderY + ballY) / 2;
  const valueText = `${value.toFixed(2)}x`;
  const subLabel = 'Peak Height';
  ctx.font = 'bold 13px monospace';
  const valueWidth = ctx.measureText(valueText).width;
  ctx.font = '10px sans-serif';
  const subWidth = ctx.measureText(subLabel).width;
  const labelWidth = Math.max(valueWidth, subWidth) + 16;
  const labelHeight = 36;
  const labelLeft = bracketX - labelWidth - 10;
  // Clamp label Y within canvas
  const rawLabelTop = midY - labelHeight / 2;
  const labelTop = Math.max(
    ANNOTATION_Y_MARGIN,
    Math.min(rawLabelTop, canvasHeight - ANNOTATION_Y_MARGIN - labelHeight)
  );

  // Backdrop
  const r = 6;
  ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
  ctx.beginPath();
  ctx.moveTo(labelLeft + r, labelTop);
  ctx.lineTo(labelLeft + labelWidth - r, labelTop);
  ctx.arcTo(
    labelLeft + labelWidth,
    labelTop,
    labelLeft + labelWidth,
    labelTop + r,
    r
  );
  ctx.arcTo(
    labelLeft + labelWidth,
    labelTop + labelHeight,
    labelLeft + labelWidth - r,
    labelTop + labelHeight,
    r
  );
  ctx.lineTo(labelLeft + r, labelTop + labelHeight);
  ctx.arcTo(
    labelLeft,
    labelTop + labelHeight,
    labelLeft,
    labelTop + labelHeight - r,
    r
  );
  ctx.arcTo(labelLeft, labelTop, labelLeft + r, labelTop, r);
  ctx.closePath();
  ctx.fill();

  // Subtle cyan border on backdrop
  ctx.strokeStyle = `rgba(0, 212, 255, 0.25)`;
  ctx.lineWidth = 1;
  ctx.stroke();

  // Value text
  ctx.fillStyle = ANNOTATION_COLOR;
  ctx.font = 'bold 13px monospace';
  ctx.textAlign = 'center';
  ctx.fillText(valueText, labelLeft + labelWidth / 2, labelTop + 16);

  // Sub-label
  ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
  ctx.font = '10px sans-serif';
  ctx.fillText(subLabel, labelLeft + labelWidth / 2, labelTop + 30);

  ctx.restore();
}

export interface TossLateralityAnnotationParams {
  ctx: CanvasRenderingContext2D;
  ballX: number;
  bodyCenterX: number;
  ballY: number;
  canvasHeight: number;
  value: number;
  opacity: number;
}

/**
 * Draw toss laterality annotation: vertical reference line at body center,
 * horizontal arrow with filled arrowhead to ball position, direction word,
 * and label backdrop.
 */
export function drawTossLateralityAnnotation(
  params: TossLateralityAnnotationParams
): void {
  const { ctx, ballX, bodyCenterX, ballY, canvasHeight, value, opacity } =
    params;

  ctx.save();
  ctx.globalAlpha = opacity;

  // Shortened vertical reference line at body center (~100px around ball Y)
  const refHalf = 50;
  ctx.strokeStyle = ANNOTATION_COLOR;
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(bodyCenterX, Math.max(0, ballY - refHalf));
  ctx.lineTo(bodyCenterX, Math.min(canvasHeight, ballY + refHalf));
  ctx.stroke();

  // Horizontal line from body center to ball
  const lineY = ballY + 20;
  ctx.setLineDash([]);
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(bodyCenterX, lineY);
  ctx.lineTo(ballX, lineY);
  ctx.stroke();

  // Filled arrowhead
  const dir = ballX > bodyCenterX ? -1 : 1;
  const arrowSize = 8;
  ctx.fillStyle = ANNOTATION_COLOR;
  ctx.beginPath();
  ctx.moveTo(ballX, lineY);
  ctx.lineTo(ballX + dir * arrowSize, lineY - arrowSize * 0.6);
  ctx.lineTo(ballX + dir * arrowSize, lineY + arrowSize * 0.6);
  ctx.closePath();
  ctx.fill();

  // Label backdrop + text
  const sign = value >= 0 ? '+' : '';
  const valueText = `${sign}${value.toFixed(2)}`;
  const dirLabel = value >= 0 ? 'Right' : 'Left';
  ctx.font = 'bold 12px monospace';
  const valWidth = ctx.measureText(valueText).width;
  ctx.font = '10px sans-serif';
  const dirWidth = ctx.measureText(dirLabel).width;
  const labelWidth = Math.max(valWidth, dirWidth) + 14;
  const labelHeight = 32;
  const labelX = (bodyCenterX + ballX) / 2 - labelWidth / 2;
  const labelTop = lineY - labelHeight - 6;
  const r = 5;

  // Backdrop
  ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
  ctx.beginPath();
  ctx.moveTo(labelX + r, labelTop);
  ctx.lineTo(labelX + labelWidth - r, labelTop);
  ctx.arcTo(
    labelX + labelWidth,
    labelTop,
    labelX + labelWidth,
    labelTop + r,
    r
  );
  ctx.arcTo(
    labelX + labelWidth,
    labelTop + labelHeight,
    labelX + labelWidth - r,
    labelTop + labelHeight,
    r
  );
  ctx.lineTo(labelX + r, labelTop + labelHeight);
  ctx.arcTo(
    labelX,
    labelTop + labelHeight,
    labelX,
    labelTop + labelHeight - r,
    r
  );
  ctx.arcTo(labelX, labelTop, labelX + r, labelTop, r);
  ctx.closePath();
  ctx.fill();

  // Subtle cyan border on backdrop
  ctx.strokeStyle = `rgba(0, 212, 255, 0.25)`;
  ctx.lineWidth = 1;
  ctx.stroke();

  // Value text
  ctx.fillStyle = ANNOTATION_COLOR;
  ctx.font = 'bold 12px monospace';
  ctx.textAlign = 'center';
  ctx.fillText(valueText, labelX + labelWidth / 2, labelTop + 14);

  // Direction sub-label
  ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
  ctx.font = '10px sans-serif';
  ctx.fillText(dirLabel, labelX + labelWidth / 2, labelTop + 26);

  ctx.restore();
}

// ---------------------------------------------------------------------------
// Contact point annotation
// ---------------------------------------------------------------------------

export interface ContactPointAnnotationParams {
  ctx: CanvasRenderingContext2D;
  x: number;
  y: number;
  opacity: number;
}

/**
 * Draw contact point annotation: crosshair + pulsing circle + "Contact" label.
 */
export function drawContactPointAnnotation(
  params: ContactPointAnnotationParams
): void {
  const { ctx, x, y, opacity } = params;

  ctx.save();
  ctx.globalAlpha = opacity;

  const crossSize = 12;
  const ringRadius = 16;

  // Outer pulsing ring
  ctx.strokeStyle = ANNOTATION_COLOR;
  ctx.lineWidth = 2;
  ctx.globalAlpha = opacity * 0.4;
  ctx.beginPath();
  ctx.arc(x, y, ringRadius, 0, Math.PI * 2);
  ctx.stroke();
  ctx.globalAlpha = opacity;

  // Inner ring
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(x, y, 6, 0, Math.PI * 2);
  ctx.stroke();

  // Crosshair lines
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(x - crossSize, y);
  ctx.lineTo(x - 8, y);
  ctx.moveTo(x + 8, y);
  ctx.lineTo(x + crossSize, y);
  ctx.moveTo(x, y - crossSize);
  ctx.lineTo(x, y - 8);
  ctx.moveTo(x, y + 8);
  ctx.lineTo(x, y + crossSize);
  ctx.stroke();

  // Center dot
  ctx.fillStyle = ANNOTATION_COLOR;
  ctx.beginPath();
  ctx.arc(x, y, 2, 0, Math.PI * 2);
  ctx.fill();

  // "Contact" label
  const label = 'Contact';
  ctx.font = 'bold 11px sans-serif';
  const textWidth = ctx.measureText(label).width;
  const padX = 6;
  const padY = 4;
  const labelX = x + crossSize + 6;
  const labelY = y - 8;

  // Label backdrop
  ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
  const bw = textWidth + padX * 2;
  const bh = 11 + padY * 2;
  const br = 4;
  ctx.beginPath();
  ctx.moveTo(labelX + br, labelY);
  ctx.lineTo(labelX + bw - br, labelY);
  ctx.arcTo(labelX + bw, labelY, labelX + bw, labelY + br, br);
  ctx.arcTo(labelX + bw, labelY + bh, labelX + bw - br, labelY + bh, br);
  ctx.lineTo(labelX + br, labelY + bh);
  ctx.arcTo(labelX, labelY + bh, labelX, labelY + bh - br, br);
  ctx.arcTo(labelX, labelY, labelX + br, labelY, br);
  ctx.closePath();
  ctx.fill();

  // Subtle cyan border on backdrop
  ctx.strokeStyle = `rgba(0, 212, 255, 0.25)`;
  ctx.lineWidth = 1;
  ctx.stroke();

  ctx.fillStyle = ANNOTATION_COLOR;
  ctx.textAlign = 'left';
  ctx.fillText(label, labelX + padX, labelY + padY + 10);

  ctx.restore();
}
