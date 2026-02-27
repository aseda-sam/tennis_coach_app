import type {
  ServeWindow,
  ServeWindowCreate,
  ServeWindowFilters,
  ServeWindowUpdate,
} from '../types/serveWindow';
import api from './api';

export type {
  CourtSide,
  InOut,
  ServeSubtype,
  ServeWindow,
  ServeWindowCreate,
  ServeWindowFilters,
  ServeWindowUpdate,
} from '../types/serveWindow';

export interface ServeWindowSplitRequest {
  split_at: number;
}

export interface ServeWindowSplitResponse {
  window_a: ServeWindow;
  window_b: ServeWindow;
}

export const serveWindowApi = {
  // Create a new serve window
  create: async (serveWindow: ServeWindowCreate): Promise<ServeWindow> => {
    const response = await api.post<ServeWindow>(
      '/serve-windows/',
      serveWindow
    );
    return response.data;
  },

  // Get a specific serve window by ID
  getById: async (serveWindowId: number): Promise<ServeWindow> => {
    const response = await api.get<ServeWindow>(
      `/serve-windows/${serveWindowId}`
    );
    return response.data;
  },

  // List serve windows for a video (demo-safe, no auth required for demo videos)
  listByVideo: async (videoId: number): Promise<ServeWindow[]> => {
    const response = await api.get<ServeWindow[]>(
      `/serve-windows/video/${videoId}`
    );
    return response.data;
  },

  // List serve windows with optional filters
  list: async (filters?: ServeWindowFilters): Promise<ServeWindow[]> => {
    const params = new URLSearchParams();
    if (filters?.player_id)
      params.append('player_id', filters.player_id.toString());
    if (filters?.court_side) params.append('court_side', filters.court_side);
    if (filters?.video_id)
      params.append('video_id', filters.video_id.toString());
    if (filters?.start_date) params.append('start_date', filters.start_date);
    if (filters?.end_date) params.append('end_date', filters.end_date);

    const queryString = params.toString();
    const url = `/serve-windows/me${queryString ? `?${queryString}` : ''}`;
    const response = await api.get<ServeWindow[]>(url);
    return response.data;
  },

  // Update a serve window
  update: async (
    serveWindowId: number,
    updates: ServeWindowUpdate
  ): Promise<ServeWindow> => {
    const response = await api.put<ServeWindow>(
      `/serve-windows/${serveWindowId}`,
      updates
    );
    return response.data;
  },

  // Delete a serve window
  delete: async (serveWindowId: number): Promise<void> => {
    await api.delete(`/serve-windows/${serveWindowId}`);
  },

  // Split a serve window at a given timestamp
  split: async (
    serveWindowId: number,
    request: ServeWindowSplitRequest
  ): Promise<ServeWindowSplitResponse> => {
    const response = await api.post<ServeWindowSplitResponse>(
      `/serve-windows/${serveWindowId}/split`,
      request
    );
    return response.data;
  },
};
