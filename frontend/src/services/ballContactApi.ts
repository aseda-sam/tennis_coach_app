import api from './api';

export interface BallContact {
  id: number;
  video_id: number;
  frame_number?: number;
  video_timestamp: number;
  player?: number;
  contact_hand: 'left' | 'right';
  stroke_type?: 'ground_stroke' | 'serve' | 'volley' | 'overhead';
  stroke_subtype?: string;
  elbow_angle?: number; // Posture analysis: elbow angle in degrees (0-180°)
  detection_source: 'automated' | 'manual';
  created_at: string;
  updated_at?: string;
}

export interface BallContactCreate {
  video_id: number;
  video_timestamp: number;
  contact_hand: 'left' | 'right';
  stroke_type?: 'ground_stroke' | 'serve' | 'volley' | 'overhead';
  stroke_subtype?: string;
  detection_source: 'automated' | 'manual';
}

export interface BallContactUpdate {
  video_timestamp?: number;
  contact_hand?: 'left' | 'right';
  stroke_type?: 'ground_stroke' | 'serve' | 'volley' | 'overhead';
  stroke_subtype?: string;
}

// Posture Analysis Interfaces
export interface PostureAnalysisResponse {
  ball_contact_id: number;
  elbow_angle?: number; // 0-180° range
  analysis_status: 'success' | 'failed' | 'no_pose_data' | 'invalid_stroke';
  message?: string;
}

export interface PostureAnalysisRequest {
  force_reanalysis?: boolean;
}

export const ballContactApi = {
  // Get all ball contacts for a video
  getContacts: async (videoId: number): Promise<BallContact[]> => {
    const response = await api.get(`/ball-contacts/video/${videoId}`);
    return response.data;
  },

  // Get contact timestamps for video player markers
  getContactTimestamps: async (videoId: number): Promise<number[]> => {
    const response = await api.get(
      `/ball-contacts/video/${videoId}/timestamps`
    );
    return response.data;
  },

  // Get a specific ball contact by ID
  getContact: async (contactId: number): Promise<BallContact> => {
    const response = await api.get(`/ball-contacts/${contactId}`);
    return response.data;
  },

  // Create a new ball contact
  createContact: async (contact: BallContactCreate): Promise<BallContact> => {
    const response = await api.post('/ball-contacts/', contact);
    return response.data;
  },

  // Update a ball contact
  updateContact: async (
    contactId: number,
    updates: BallContactUpdate
  ): Promise<BallContact> => {
    const response = await api.put(`/ball-contacts/${contactId}`, updates);
    return response.data;
  },

  // Delete a ball contact
  deleteContact: async (contactId: number): Promise<void> => {
    await api.delete(`/ball-contacts/${contactId}`);
  },

  // Posture Analysis Methods
  // Get posture analysis for a specific ball contact
  getPostureAnalysis: async (
    contactId: number
  ): Promise<PostureAnalysisResponse> => {
    const response = await api.get(
      `/ball-contacts/${contactId}/posture-analysis`
    );
    return response.data;
  },

  // Analyze posture for a specific ball contact
  analyzePosture: async (
    contactId: number,
    request: PostureAnalysisRequest = {}
  ): Promise<PostureAnalysisResponse> => {
    const response = await api.post(
      `/ball-contacts/${contactId}/analyze-posture`,
      request
    );
    return response.data;
  },

  // Analyze posture for all ball contacts in a video
  analyzeVideoPosture: async (
    videoId: number,
    request: PostureAnalysisRequest = {}
  ): Promise<PostureAnalysisResponse[]> => {
    const response = await api.post(
      `/ball-contacts/video/${videoId}/analyze-posture`,
      request
    );
    return response.data;
  },
};
