import api from './api';

export type CourtSide = 'deuce' | 'ad';
export type ServeSubtype = 'flat' | 'slice' | 'kick';
export type InOut = 'in' | 'out_long' | 'out_wide' | 'net' | 'unknown';

export interface ServeWindow {
  id: number;
  video_id: number;
  player_id: number;
  start_timestamp: number;
  end_timestamp: number;
  contact_timestamp: number | null;
  source: string;
  status: string;
  confidence: number | null;
  model_version: string | null;
  court_side: CourtSide | null;
  serve_number: number | null;
  serve_subtype: ServeSubtype | null;
  in_out: InOut | null;
  created_at: string;
}

export interface ServeWindowCreate {
  video_id: number;
  player_id?: number | null;
  start_timestamp: number;
  end_timestamp: number;
  contact_timestamp?: number | null;
  court_side?: CourtSide | null;
  serve_number?: number | null;
  serve_subtype?: ServeSubtype | null;
  in_out?: InOut | null;
}

export interface ServeWindowUpdate {
  player_id?: number | null;
  start_timestamp?: number | null;
  end_timestamp?: number | null;
  contact_timestamp?: number | null;
  court_side?: CourtSide | null;
  serve_number?: number | null;
  serve_subtype?: ServeSubtype | null;
  in_out?: InOut | null;
}

export interface ServeWindowFilters {
  player_id?: number;
  court_side?: CourtSide;
  video_id?: number;
  start_date?: string;
  end_date?: string;
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
};
