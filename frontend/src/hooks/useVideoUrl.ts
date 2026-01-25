import { useQuery } from '@tanstack/react-query';
import { videoApi } from '../services/api';

interface UseVideoUrlOptions {
  videoId: number | undefined;
  videoUrl: string;
  expiresIn?: number;
}

export const useVideoUrl = ({
  videoId,
  videoUrl,
  expiresIn = 3600,
}: UseVideoUrlOptions): {
  resolvedUrl: string;
  isLoading: boolean;
  error: Error | null;
} => {
  // Only use signed URL API if we have a videoId and the URL is a stream endpoint
  const shouldFetchSignedUrl = !!videoId && videoUrl.includes('/stream');

  const urlQuery = useQuery<string>({
    queryKey: ['video-url', videoId, expiresIn],
    queryFn: async () => {
      if (!videoId) {
        return videoUrl;
      }
      return await videoApi.getVideoUrl(videoId, expiresIn);
    },
    enabled: shouldFetchSignedUrl,
    staleTime: expiresIn * 1000 * 0.9, // Cache for 90% of expiry time
    gcTime: expiresIn * 1000, // Keep in cache for full expiry time
  });

  // Return resolved URL: use signed URL if available, fallback to original URL on error or when not fetching
  const resolvedUrl = shouldFetchSignedUrl
    ? urlQuery.data || (urlQuery.error ? videoUrl : '')
    : videoUrl;

  return {
    resolvedUrl,
    isLoading: urlQuery.isLoading,
    error: urlQuery.error as Error | null,
  };
};
