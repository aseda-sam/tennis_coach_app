import api from './api';

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
  serve_attempt_id?: number | null;
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

export const serveProposalApi = {
  // Run detection and generate proposals
  propose: async (videoId: number): Promise<ProposeResponse> => {
    const response = await api.post<ProposeResponse>(
      `/videos/${videoId}/serve-detection/propose`
    );
    return response.data;
  },

  // Get proposals for a video
  list: async (videoId: number): Promise<ServeWindowProposal[]> => {
    const response = await api.get<ServeWindowProposal[]>(
      `/videos/${videoId}/serve-detection/proposals`
    );
    return response.data;
  },

  // Accept a proposal
  accept: async (
    proposalId: number,
    request?: AcceptProposalRequest
  ): Promise<void> => {
    await api.post(
      `/serve-detection/proposals/${proposalId}/accept`,
      request || {}
    );
  },

  // Reject a proposal
  reject: async (proposalId: number): Promise<void> => {
    await api.post(`/serve-detection/proposals/${proposalId}/reject`);
  },

  // Accept with edits
  edit: async (
    proposalId: number,
    request: EditProposalRequest
  ): Promise<void> => {
    await api.post(`/serve-detection/proposals/${proposalId}/edit`, request);
  },
};
