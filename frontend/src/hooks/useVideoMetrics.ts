import { useQuery } from '@tanstack/react-query';
import { videoApi } from '../services/api';
import type { VideoMetrics } from '../types/video';

export const useVideoMetrics = (videoId: number) => {
  return useQuery<VideoMetrics, Error>({
    queryKey: ['video-metrics', videoId],
    queryFn: async () => {
      return await videoApi.getVideoMetrics(videoId);
    },
    staleTime: 2 * 60 * 1000, // 2 minutes - metrics don't change often
  });
};
