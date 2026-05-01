/** Serve biomechanics API types (phases + raw metrics only, no scoring). */

export interface CoachingFeedbackResponse {
  feedback: string;
  model: string;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
}

export interface CoachingNoteResponse {
  serve_window_id: number;
  note: string;
  timestamp: number;
  user_id: number;
}

export interface MetricValue {
  metric_name: string;
  value: number | null;
  unit: string;
  phase: string | null;
  timestamp?: number; // seconds — when this metric was measured
}

export interface PhaseWindow {
  phase: string;
  phase_label: string;
  start_timestamp: number;
  end_timestamp: number;
  confidence: number;
  detected: boolean;
}

export interface KTPDetail {
  frame: number;
  timestamp?: number;
  method: string;
  search_window?: [number, number];
  [key: string]: unknown;
}

export interface DetectionMeta {
  ktps: Record<string, KTPDetail | null>;
  feature_curves: {
    max_wrist_height: number[];
    knee_hip_ratio: number[];
    max_wrist_velocity: number[];
  };
  fps: number;
  total_frames: number;
}

export interface MomentMarker {
  moment: string;
  moment_label: string;
  timestamp: number | null;
  frame: number | null;
  confidence: number;
  detected: boolean;
}

export interface ServeBiomechanicsReport {
  id: number;
  serve_window_id: number;
  phase_segmentation: PhaseWindow[];
  moments: MomentMarker[];
  metrics: MetricValue[];
  analysis_version: string;
  detection_meta?: DetectionMeta | null;
  player_id?: number | null;
  created_at: string;
  video_id?: number | null;
  video_filename?: string | null;
  video_recorded_at?: string | null;
}
