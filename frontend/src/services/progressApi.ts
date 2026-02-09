import api from './api';

export interface ProgressMetricDataPoint {
  date: string;
  avg: number;
  count: number;
}

export interface ElbowAngleMetric {
  current_avg: number;
  previous_avg: number | null;
  trend: 'improving' | 'declining' | 'stable';
  consistency: number;
  consistency_rating: 'excellent' | 'good' | 'fair' | 'needs_work';
  data_points: ProgressMetricDataPoint[];
}

export interface KneeBendMetric {
  current_rate: number;
  previous_rate: number | null;
  trend: 'improving' | 'declining' | 'stable';
  data_points: ProgressMetricDataPoint[];
}

export interface CourtSideDistribution {
  deuce: number;
  ad: number;
  unknown: number;
}

export interface ProgressMetrics {
  elbow_angle: ElbowAngleMetric | null;
  knee_bend: KneeBendMetric | null;
}

export interface ProgressResponse {
  time_period: string;
  total_serves: number;
  total_videos: number;
  metrics: ProgressMetrics;
  court_side: CourtSideDistribution;
}

export const progressApi = {
  fetchProgress: async (
    timePeriod: string = '30d',
    playerId?: number
  ): Promise<ProgressResponse> => {
    const params = new URLSearchParams();
    params.append('time_period', timePeriod);
    if (playerId) params.append('player_id', playerId.toString());

    const url = `/progress/me?${params.toString()}`;
    const response = await api.get<ProgressResponse>(url);
    return response.data;
  },
};
