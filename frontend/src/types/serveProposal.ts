/** Serve detection proposal types. */

export interface ServeWindowProposal {
  id: number;
  video_id: number;
  start_timestamp: number;
  end_timestamp: number;
  model_version: string;
  confidence: number;
  detection_features?: {
    peak_frame?: number;
    peak_wrist_height?: number;
    peak_wrist_velocity?: number;
  } | null;
  status: 'pending' | 'accepted' | 'rejected' | 'edited';
  created_at: string;
  reviewed_at?: string | null;
}

export interface ProposeResponse {
  video_id: number;
  proposals: ServeWindowProposal[];
  count: number;
}

export interface AcceptProposalRequest {
  player_id?: number | null;
}

export interface EditProposalRequest {
  start_timestamp: number;
  end_timestamp: number;
  player_id?: number | null;
}

export interface DetectionStatusResponse {
  video_id: number;
  pending_proposals: number;
  reviewed_proposals: number;
  serve_windows: number;
  can_run_detection: boolean;
}

export interface ClearProposalsResponse {
  video_id: number;
  cleared_count: number;
}

export interface BulkAcceptRequest {
  player_id?: number | null;
}

export interface BulkAcceptResponse {
  video_id: number;
  accepted_count: number;
  serve_window_ids: number[];
}

export interface RejectByConfidenceRequest {
  threshold: number;
}

export interface RejectByConfidenceResponse {
  video_id: number;
  rejected_count: number;
  threshold: number;
}
