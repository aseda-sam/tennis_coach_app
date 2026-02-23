/** Serve detection proposal types. */

export interface ProposeResponse {
  video_id: number;
  proposals: unknown[];
  count: number;
}

export interface DetectionStatusResponse {
  video_id: number;
  pending_proposals: number;
  reviewed_proposals: number;
  serve_windows: number;
  can_run_detection: boolean;
}
