import { useQuery } from '@tanstack/react-query';
import { videoApi } from '../services/api';
import type { VideoMetrics, VideoMetricsByVideo } from '../types/video';

export const useVideoMetrics = (videoId: number) => {
  return useQuery<VideoMetrics, Error>({
    queryKey: ['video-metrics', videoId],
    queryFn: async () => {
      return await videoApi.getVideoMetrics(videoId);
    },
    staleTime: 2 * 60 * 1000, // 2 minutes - metrics don't change often
  });
};

export const useVideoMetricsBulk = (videoIds: number[]) => {
  const key = [...videoIds].sort((a, b) => a - b).join(',');

  return useQuery<VideoMetricsByVideo, Error>({
    queryKey: ['video-metrics-bulk', key],
    queryFn: async () => {
      if (videoIds.length === 0) {
        return {};
      }
      return await videoApi.getBulkVideoMetrics(videoIds);
    },
    enabled: videoIds.length > 0,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};
