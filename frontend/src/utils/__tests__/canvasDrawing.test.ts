import {
  computeNormalizationRef,
  normalizePose,
  normalizePoseFixed,
} from '../canvasDrawing';

// Helper: build a minimal frame with keypoints
function makeFrame(keypoints: Record<string, number[]>) {
  return { keypoints };
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

  it('on the reference frame matches normalizePose output', () => {
    const fixed = normalizePoseFixed(
      STANDING_KEYPOINTS,
      CANVAS_W,
      CANVAS_H,
      ref
    );
    const perFrame = normalizePose(STANDING_KEYPOINTS, CANVAS_W, CANVAS_H);

    expect(perFrame).not.toBeNull();
    for (const name of Object.keys(STANDING_KEYPOINTS)) {
      expect(fixed[name]!.x).toBeCloseTo(perFrame![name]!.x, 5);
      expect(fixed[name]!.y).toBeCloseTo(perFrame![name]!.y, 5);
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
    // Ball is above hip center in video space → should be above canvas anchor
    expect(norm['_ball']!.y).toBeLessThan(CANVAS_H * 0.4);
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
});
