import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
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
    queryFn: () => videoApi.getVideoAnalysisStatus(videoId),
    staleTime: 2 * 60 * 1000, // 2 minutes - analysis status doesn't change often
    refetchOnWindowFocus: false, // Don't refetch when window regains focus
    refetchOnMount: false, // Don't refetch on component mount if data is fresh
    refetchInterval: false, // Disable automatic polling - we'll refetch manually when needed
  });
};

export const useVideoAnalysisStatuses = (videoIds: number[]) => {
  const key = [...videoIds].sort((a, b) => a - b).join(',');

  return useQuery<VideoAnalysisStatusById, Error>({
    queryKey: ['video-analysis-statuses', key],
    queryFn: async () => {
      if (videoIds.length === 0) {
        return {};
      }

      const statuses = await videoApi.getBulkVideoAnalysisStatus(videoIds);
      return statuses.reduce((acc, status) => {
        acc[status.video_id] = status;
        return acc;
      }, {} as VideoAnalysisStatusById);
    },
    enabled: videoIds.length > 0,
    staleTime: 2 * 60 * 1000,
  });
};

export const useVideoMetadata = (videoId: number | undefined) => {
  return useQuery<VideoMetadata, Error>({
    queryKey: ['video', videoId],
    queryFn: async () => {
      if (!videoId) {
        throw new Error('Video ID is required');
      }
      return await videoApi.getVideo(videoId);
    },
    enabled: !!videoId,
    staleTime: 5 * 60 * 1000, // 5 minutes - video metadata doesn't change often
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

export const useUploadVideo = () => {
  return useMutation({
    mutationFn: ({
      file,
      isDemo,
      clientRecordedAt,
      metadata,
    }: {
      file: File;
      isDemo: boolean;
      clientRecordedAt?: string;
      metadata?: { session_type?: string; camera_angle?: string };
    }) => videoApi.uploadVideo(file, isDemo, clientRecordedAt, metadata),
  });
};

export const useUpdateVideoMetadata = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      videoId,
      metadata,
    }: {
      videoId: number;
      metadata: {
        session_type?: string;
        camera_angle?: string;
        player_tag?: 'you' | 'someone_else';
        apply_to_existing_serves?: boolean;
      };
    }) => videoApi.updateVideoMetadata(videoId, metadata),
    onSuccess: (updatedVideo, { videoId }) => {
      queryClient.setQueryData(['video', videoId], updatedVideo);
      queryClient.invalidateQueries({ queryKey: ['videos'] });
    },
  });
};
