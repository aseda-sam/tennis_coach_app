import {
  computeNormalizationRef,
  normalizePoseFixed,
  HEAD_OFFSET_RATIO,
  HEAD_RADIUS,
  MIN_EXTENT_TORSOS,
  SCENE_BOTTOM_MARGIN,
  SCENE_TOP_MARGIN,
} from '../canvasDrawing';

// Helper: build a minimal frame with keypoints and optional ball
function makeFrame(
  keypoints: Record<string, number[]>,
  ball_position?: number[]
) {
  return { keypoints, ball_position };
}

// Reference keypoints for a standing figure (video pixel space)
const STANDING_KEYPOINTS: Record<string, number[]> = {
  left_shoulder: [480, 200],
  right_shoulder: [560, 200],
  left_hip: [490, 350],
  right_hip: [550, 350],
  left_knee: [485, 480],
  right_knee: [555, 480],
  left_ankle: [480, 600],
  right_ankle: [560, 600],
  left_elbow: [440, 280],
  right_elbow: [600, 280],
  left_wrist: [420, 350],
  right_wrist: [620, 350],
};

const CANVAS_W = 400;
const CANVAS_H = 500;

describe('computeNormalizationRef', () => {
  it('returns correct values from a valid frame', () => {
    const frames = [makeFrame(STANDING_KEYPOINTS)];
    const ref = computeNormalizationRef(frames, undefined, 30);

    expect(ref).not.toBeNull();
    // Hip center = midpoint of left_hip and right_hip
    expect(ref!.hipCenterX).toBe((490 + 550) / 2); // 520
    expect(ref!.hipCenterY).toBe((350 + 350) / 2); // 350
    // Torso length = distance from hip center to shoulder center
    const shCenterX = (480 + 560) / 2; // 520
    const shCenterY = (200 + 200) / 2; // 200
    const expectedTorso = Math.sqrt(
      (shCenterX - 520) ** 2 + (shCenterY - 350) ** 2
    );
    expect(ref!.torsoLength).toBeCloseTo(expectedTorso);
    // Ground Y = max ankle Y
    expect(ref!.groundY).toBe(600);
    // topY = head estimate (no ball data)
    expect(ref!.topY).toBeDefined();
    expect(ref!.topY).toBeLessThan(shCenterY);
  });

  it('skips frames with missing keypoints and uses next valid frame', () => {
    const badFrame = makeFrame({
      left_shoulder: [100, 100],
      // Missing right_shoulder, hips
    });
    const goodFrame = makeFrame(STANDING_KEYPOINTS);
    const frames = [badFrame, goodFrame];

    const ref = computeNormalizationRef(frames, undefined, 30);
    expect(ref).not.toBeNull();
    expect(ref!.hipCenterX).toBe(520);
  });

  it('returns null when no valid frames exist', () => {
    const badFrames = [
      makeFrame({ left_shoulder: [100, 100] }),
      makeFrame({ right_hip: [200, 200] }),
    ];
    const ref = computeNormalizationRef(badFrames, undefined, 30);
    expect(ref).toBeNull();
  });

  it('returns null for empty frames array', () => {
    const ref = computeNormalizationRef([], undefined, 30);
    expect(ref).toBeNull();
  });

  it('handles missing ankles by falling back to hip + 2*torso', () => {
    const noAnkles: Record<string, number[]> = {
      left_shoulder: [480, 200],
      right_shoulder: [560, 200],
      left_hip: [490, 350],
      right_hip: [550, 350],
    };
    const frames = [makeFrame(noAnkles)];
    const ref = computeNormalizationRef(frames, undefined, 30);

    expect(ref).not.toBeNull();
    // groundY should be hipCenterY + torsoLength * 2
    expect(ref!.groundY).toBe(ref!.hipCenterY + ref!.torsoLength * 2);
  });

  it('uses serveStartTime to pick the starting frame', () => {
    // Frame 0: different keypoints
    const frame0 = makeFrame({
      left_shoulder: [100, 100],
      right_shoulder: [200, 100],
      left_hip: [110, 250],
      right_hip: [190, 250],
      left_ankle: [100, 400],
      right_ankle: [200, 400],
    });
    const frame1 = makeFrame(STANDING_KEYPOINTS);

    const fps = 30;
    // serveStartTime = 1/30 → frame index 1
    const ref = computeNormalizationRef([frame0, frame1], 1 / fps, fps);
    expect(ref).not.toBeNull();
    expect(ref!.hipCenterX).toBe(520); // from frame1's keypoints
  });

  it('computes topY from ball positions across frames', () => {
    const highBallY = 50; // Ball tossed very high (low Y in video coords)
    const frames = [
      makeFrame(STANDING_KEYPOINTS, [520, 300]), // ball near body
      makeFrame(STANDING_KEYPOINTS, [520, highBallY]), // ball at peak
      makeFrame(STANDING_KEYPOINTS, [520, 200]), // ball descending
    ];
    const ref = computeNormalizationRef(frames, undefined, 30);

    expect(ref).not.toBeNull();
    // topY should be at or below the highest ball position
    expect(ref!.topY).toBeLessThanOrEqual(highBallY);
  });

  it('uses head estimate when no ball data present', () => {
    const frames = [makeFrame(STANDING_KEYPOINTS)]; // no ball_position
    const ref = computeNormalizationRef(frames, undefined, 30);

    expect(ref).not.toBeNull();
    // Head estimate should be above shoulder center
    const shoulderCenterY = 200;
    const expectedHead =
      shoulderCenterY -
      ref!.torsoLength * (HEAD_OFFSET_RATIO + HEAD_RADIUS / ref!.torsoLength);
    expect(ref!.topY).toBeCloseTo(expectedHead);
  });

  it('caps topY at 8 torso lengths above hips for noisy detections', () => {
    // Ball at absurdly high position (noisy detection)
    const frames = [makeFrame(STANDING_KEYPOINTS, [520, -5000])];
    const ref = computeNormalizationRef(frames, undefined, 30);

    expect(ref).not.toBeNull();
    // Sanity cap: topY >= hipCenterY - torsoLength * 8
    expect(ref!.topY).toBeGreaterThanOrEqual(
      ref!.hipCenterY - ref!.torsoLength * 8
    );
  });
});

describe('normalizePoseFixed', () => {
  const ref = computeNormalizationRef(
    [makeFrame(STANDING_KEYPOINTS)],
    undefined,
    30
  )!;

  it('produces identical output for two different frames given the same ref', () => {
    // Simulate a different frame where the player shifted right by 20px
    const shiftedKeypoints: Record<string, number[]> = {};
    for (const [name, coords] of Object.entries(STANDING_KEYPOINTS)) {
      shiftedKeypoints[name] = [coords[0] + 20, coords[1] - 10];
    }

    const norm1 = normalizePoseFixed(
      STANDING_KEYPOINTS,
      CANVAS_W,
      CANVAS_H,
      ref
    );
    const norm2 = normalizePoseFixed(shiftedKeypoints, CANVAS_W, CANVAS_H, ref);

    // They should NOT be identical (the player moved!) — this proves the
    // reference frame is fixed and real movement shows through.
    expect(norm1['left_shoulder']!.x).not.toBeCloseTo(
      norm2['left_shoulder']!.x
    );

    // But calling with the SAME keypoints twice should be identical (stability)
    const norm1b = normalizePoseFixed(
      STANDING_KEYPOINTS,
      CANVAS_W,
      CANVAS_H,
      ref
    );
    expect(norm1['left_shoulder']!.x).toBeCloseTo(norm1b['left_shoulder']!.x);
    expect(norm1['left_shoulder']!.y).toBeCloseTo(norm1b['left_shoulder']!.y);
  });

  it('places ground near canvas bottom and figure within margins', () => {
    const norm = normalizePoseFixed(
      STANDING_KEYPOINTS,
      CANVAS_W,
      CANVAS_H,
      ref
    );

    // Ground should map near the bottom margin line
    const groundCanvasY = CANVAS_H * (1 - SCENE_BOTTOM_MARGIN);
    const ankleY = Math.max(norm['left_ankle']!.y, norm['right_ankle']!.y);
    // Ankles should be near the ground line (at or slightly above)
    expect(ankleY).toBeLessThanOrEqual(groundCanvasY);
    expect(ankleY).toBeGreaterThan(groundCanvasY - CANVAS_H * 0.15);

    // Head area should be above top margin
    const shoulderY =
      (norm['left_shoulder']!.y + norm['right_shoulder']!.y) / 2;
    expect(shoulderY).toBeGreaterThan(CANVAS_H * SCENE_TOP_MARGIN);

    // Figure should be vertically within canvas bounds
    for (const name of Object.keys(STANDING_KEYPOINTS)) {
      expect(norm[name]!.y).toBeGreaterThan(0);
      expect(norm[name]!.y).toBeLessThan(CANVAS_H);
    }
  });

  it('works with non-skeleton keys like _ball', () => {
    const withBall = {
      ...STANDING_KEYPOINTS,
      _ball: [520, 100],
    };
    const norm = normalizePoseFixed(withBall, CANVAS_W, CANVAS_H, ref);

    expect(norm['_ball']).toBeDefined();
    expect(typeof norm['_ball']!.x).toBe('number');
    expect(typeof norm['_ball']!.y).toBe('number');
    // Ball is above hip center in video space → should be above shoulders on canvas
    const shoulderY =
      (norm['left_shoulder']!.y + norm['right_shoulder']!.y) / 2;
    expect(norm['_ball']!.y).toBeLessThan(shoulderY);
  });

  it('does not require frame hips/shoulders to be present', () => {
    // Only wrists — no hips or shoulders in the keypoints
    const partialKeypoints = {
      left_wrist: [420, 350],
      right_wrist: [620, 350],
    };
    const norm = normalizePoseFixed(partialKeypoints, CANVAS_W, CANVAS_H, ref);

    expect(norm['left_wrist']).toBeDefined();
    expect(norm['right_wrist']).toBeDefined();
  });

  it('with ball data places ball peak above figure', () => {
    // Compute ref with ball data — ball at 1.5x body height above shoulders
    const ballPeakY = 50;
    const framesWithBall = [makeFrame(STANDING_KEYPOINTS, [520, ballPeakY])];
    const refWithBall = computeNormalizationRef(framesWithBall, undefined, 30)!;
    expect(refWithBall).not.toBeNull();

    const withBall = {
      ...STANDING_KEYPOINTS,
      _ball: [520, ballPeakY],
    };
    const norm = normalizePoseFixed(withBall, CANVAS_W, CANVAS_H, refWithBall);

    // Ball peak should render above the head (above shoulder Y)
    const shoulderY =
      (norm['left_shoulder']!.y + norm['right_shoulder']!.y) / 2;
    expect(norm['_ball']!.y).toBeLessThan(shoulderY);

    // Ball should still be on canvas (Y > 0)
    expect(norm['_ball']!.y).toBeGreaterThan(0);

    // Ankles should still be in the lower portion of the canvas
    const ankleY = Math.max(norm['left_ankle']!.y, norm['right_ankle']!.y);
    expect(ankleY).toBeGreaterThan(CANVAS_H * 0.5);
  });

  it('scale floors at MIN_EXTENT_TORSOS when extent is small', () => {
    // Create a compact figure where groundY - topY < torsoLength * MIN_EXTENT_TORSOS
    const compactKeypoints: Record<string, number[]> = {
      left_shoulder: [490, 300],
      right_shoulder: [510, 300],
      left_hip: [492, 340],
      right_hip: [508, 340],
      left_ankle: [490, 380],
      right_ankle: [510, 380],
    };
    const compactFrames = [makeFrame(compactKeypoints)];
    const compactRef = computeNormalizationRef(compactFrames, undefined, 30)!;
    expect(compactRef).not.toBeNull();

    // Verify the floor kicks in
    const rawExtent = compactRef.groundY - compactRef.topY;
    const floorExtent = compactRef.torsoLength * MIN_EXTENT_TORSOS;
    expect(rawExtent).toBeLessThan(floorExtent);

    // The figure should still render reasonably (not absurdly large)
    const norm = normalizePoseFixed(
      compactKeypoints,
      CANVAS_W,
      CANVAS_H,
      compactRef
    );
    const shoulderY =
      (norm['left_shoulder']!.y + norm['right_shoulder']!.y) / 2;
    const ankleY = Math.max(norm['left_ankle']!.y, norm['right_ankle']!.y);
    const figureHeight = ankleY - shoulderY;

    // Figure height should be reasonable — not fill the entire canvas
    expect(figureHeight).toBeLessThan(CANVAS_H * 0.8);
    expect(figureHeight).toBeGreaterThan(0);
  });
});
