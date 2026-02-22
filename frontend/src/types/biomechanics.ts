/** Serve biomechanics API types (phases + raw metrics only, no scoring). */

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

export interface ServeBiomechanicsReport {
  id: number;
  serve_window_id: number;
  phase_segmentation: PhaseWindow[];
  metrics: MetricValue[];
  analysis_version: string;
  detection_meta?: DetectionMeta | null;
  created_at: string;
}
