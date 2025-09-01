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

export const ballContactApi = {
  // Get all ball contacts for a video
  getContacts: async (videoId: number): Promise<BallContact[]> => {
    const response = await api.get(`/ball-contacts/video/${videoId}`);
    return response.data;
  },

  // Get contact timestamps for video player markers
  getContactTimestamps: async (videoId: number): Promise<number[]> => {
    const response = await api.get(`/ball-contacts/video/${videoId}/timestamps`);
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
};
