import api from './api';

export interface ServeAttempt {
  id: number;
  video_id: number;
  player_id: number;
  start_timestamp: number;
  end_timestamp: number;
  contact_timestamp: number | null;
  elbow_angle_at_contact: number | null;
  knee_bend_detected: boolean | null;
  knee_bend_confidence: number | null;
  knee_hip_ratio_min: number | null;
  knee_flexion_min_deg_left: number | null;
  knee_flexion_min_deg_right: number | null;
  analysis_version: string | null;
  court_side: string | null;
  serve_number: number | null;
  serve_subtype: string | null;
  in_out: string | null;
  created_at: string;
}

export interface ServeAttemptCreate {
  video_id: number;
  player_id?: number | null;
  start_timestamp: number;
  end_timestamp: number;
  contact_timestamp?: number | null;
  court_side?: string | null;
  serve_number?: number | null;
  serve_subtype?: string | null;
  in_out?: string | null;
}

export interface ServeAttemptUpdate {
  player_id?: number | null;
  start_timestamp?: number | null;
  end_timestamp?: number | null;
  contact_timestamp?: number | null;
  court_side?: string | null;
  serve_number?: number | null;
  serve_subtype?: string | null;
  in_out?: string | null;
}

export interface ServeAttemptFilters {
  player_id?: number;
  court_side?: string;
  video_id?: number;
  start_date?: string;
  end_date?: string;
}

export interface ServeAnalysisSummary {
  video_id: number;
  total_serves: number;
  serves_with_contact: number;
  avg_elbow_angle: number | null;
  knee_bend_analyzed: number;
  knee_bend_failed: number;
}

export const serveAttemptApi = {
  // Create a new serve attempt
  create: async (serveAttempt: ServeAttemptCreate): Promise<ServeAttempt> => {
    const response = await api.post<ServeAttempt>('/serve-attempts/', serveAttempt);
    return response.data;
  },

  // Get a specific serve attempt by ID
  getById: async (serveAttemptId: number): Promise<ServeAttempt> => {
    const response = await api.get<ServeAttempt>(`/serve-attempts/${serveAttemptId}`);
    return response.data;
  },

  // List serve attempts with optional filters
  list: async (filters?: ServeAttemptFilters): Promise<ServeAttempt[]> => {
    const params = new URLSearchParams();
    if (filters?.player_id) params.append('player_id', filters.player_id.toString());
    if (filters?.court_side) params.append('court_side', filters.court_side);
    if (filters?.video_id) params.append('video_id', filters.video_id.toString());
    if (filters?.start_date) params.append('start_date', filters.start_date);
    if (filters?.end_date) params.append('end_date', filters.end_date);

    const queryString = params.toString();
    const url = `/serve-attempts/me${queryString ? `?${queryString}` : ''}`;
    const response = await api.get<ServeAttempt[]>(url);
    return response.data;
  },

  // Update a serve attempt
  update: async (
    serveAttemptId: number,
    updates: ServeAttemptUpdate
  ): Promise<ServeAttempt> => {
    const response = await api.put<ServeAttempt>(
      `/serve-attempts/${serveAttemptId}`,
      updates
    );
    return response.data;
  },

  // Delete a serve attempt
  delete: async (serveAttemptId: number): Promise<void> => {
    await api.delete(`/serve-attempts/${serveAttemptId}`);
  },

  // Trigger serve analysis for a video
  analyzeServes: async (videoId: number): Promise<ServeAnalysisSummary> => {
    const response = await api.post<ServeAnalysisSummary>(
      `/videos/${videoId}/analyze-serves`
    );
    return response.data;
  },
};
