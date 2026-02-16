/** Serve biomechanics API types (phases + raw metrics only, no scoring). */

export interface MetricValue {
  metric_name: string;
  value: number | null;
  unit: string;
  phase: string | null;
}

export interface PhaseWindow {
  phase: string;
  phase_label: string;
  start_timestamp: number;
  end_timestamp: number;
  confidence: number;
  detected: boolean;
}

export interface ServeBiomechanicsReport {
  id: number;
  serve_attempt_id: number;
  phase_segmentation: PhaseWindow[];
  metrics: MetricValue[];
  analysis_version: string;
  created_at: string;
}
