import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { videoApi } from '../services/api';
import type { VideoMetadata } from '../types/video';

export type VideoAnalysisStatus = {
  video_id: number;
  has_analysis: boolean;
  analysis_types: string[];
};

export type VideoAnalysisStatusById = Record<number, VideoAnalysisStatus>;

export const useVideos = () => {
  return useQuery<VideoMetadata[], Error>({
    queryKey: ['videos'],
    queryFn: async () => {
      const response = await videoApi.getVideos();
      return response.videos;
    },
  });
};

export const useVideoAnalysisStatus = (videoId: number) => {
  return useQuery<VideoAnalysisStatus, Error>({
    queryKey: ['video-analysis-status', videoId],
    queryFn: async () => {
      try {
        return await videoApi.getVideoAnalysisStatus(videoId);
      } catch (error) {
        // Return default status if no analysis exists
        return {
          video_id: videoId,
          has_analysis: false,
          analysis_types: [],
        };
      }
    },
    staleTime: 2 * 60 * 1000, // 2 minutes - analysis status doesn't change often
  });
};

export const useVideoAnalysisStatuses = (videoIds: number[]) => {
  const key = [...videoIds].sort((a, b) => a - b).join(',');

  return useQuery<VideoAnalysisStatusById, Error>({
    queryKey: ['video-analysis-statuses', key],
    queryFn: async () => {
      // Use bulk endpoint for efficient fetching
      if (videoIds.length === 0) {
        return {};
      }

      try {
        const statuses = await videoApi.getBulkVideoAnalysisStatus(videoIds);
        // Convert to plain object for React Query serialization
        return statuses.reduce((acc, status) => {
          acc[status.video_id] = status;
          return acc;
        }, {} as VideoAnalysisStatusById);
      } catch (error) {
        // Fallback: return empty statuses for all videos
        console.error('Error fetching bulk analysis statuses:', error);
        return videoIds.reduce((acc, videoId) => {
          acc[videoId] = {
            video_id: videoId,
            has_analysis: false,
            analysis_types: [],
          };
          return acc;
        }, {} as VideoAnalysisStatusById);
      }
    },
    enabled: videoIds.length > 0,
    staleTime: 2 * 60 * 1000,
  });
};

export const useDeleteVideo = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (videoId: number) => videoApi.deleteVideo(videoId),
    onSuccess: () => {
      // Invalidate videos list to refetch
      queryClient.invalidateQueries({ queryKey: ['videos'] });
      // Also invalidate all analysis status queries
      queryClient.invalidateQueries({ queryKey: ['video-analysis-status'] });
    },
  });
};
