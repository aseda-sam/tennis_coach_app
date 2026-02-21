import type {
  AcceptProposalRequest,
  BulkAcceptRequest,
  BulkAcceptResponse,
  ClearProposalsResponse,
  DetectionStatusResponse,
  EditProposalRequest,
  ProposeResponse,
  RejectByConfidenceResponse,
  ServeWindowProposal,
} from '../types/serveProposal';
import api from './api';

export type {
  AcceptProposalRequest,
  BulkAcceptRequest,
  BulkAcceptResponse,
  ClearProposalsResponse,
  DetectionStatusResponse,
  EditProposalRequest,
  ProposeResponse,
  RejectByConfidenceRequest,
  RejectByConfidenceResponse,
  ServeWindowProposal,
} from '../types/serveProposal';

export const serveProposalApi = {
  // Get detection status for a video
  getStatus: async (videoId: number): Promise<DetectionStatusResponse> => {
    const response = await api.get<DetectionStatusResponse>(
      `/videos/${videoId}/serve-detection/status`
    );
    return response.data;
  },

  // Run detection and generate proposals
  propose: async (
    videoId: number,
    force: boolean = false
  ): Promise<ProposeResponse> => {
    const response = await api.post<ProposeResponse>(
      `/videos/${videoId}/serve-detection/propose`,
      null,
      { params: { force } }
    );
    return response.data;
  },

  // Clear all pending proposals
  clearProposals: async (videoId: number): Promise<ClearProposalsResponse> => {
    const response = await api.delete<ClearProposalsResponse>(
      `/videos/${videoId}/serve-detection/proposals`
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

  // Bulk accept all pending proposals
  acceptAll: async (
    videoId: number,
    request?: BulkAcceptRequest
  ): Promise<BulkAcceptResponse> => {
    const response = await api.post<BulkAcceptResponse>(
      `/videos/${videoId}/serve-detection/proposals/accept-all`,
      request || {}
    );
    return response.data;
  },

  // Reject proposals below confidence threshold
  rejectByConfidence: async (
    videoId: number,
    threshold: number = 0.6
  ): Promise<RejectByConfidenceResponse> => {
    const response = await api.post<RejectByConfidenceResponse>(
      `/videos/${videoId}/serve-detection/proposals/reject-by-confidence`,
      { threshold }
    );
    return response.data;
  },
};
