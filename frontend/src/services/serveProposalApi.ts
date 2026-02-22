import type {
  DetectionStatusResponse,
  ProposeResponse,
} from '../types/serveProposal';
import api from './api';

export type {
  DetectionStatusResponse,
  ProposeResponse,
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
};
