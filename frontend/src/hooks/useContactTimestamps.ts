import { useQuery } from '@tanstack/react-query';
import { videoApi } from '../services/api';

export const contactTimestampsQueryKey = (videoId: number) =>
  ['ball-contact-timestamps', videoId] as const;

export function useContactTimestamps(videoId: number | undefined) {
  const query = useQuery({
    queryKey: contactTimestampsQueryKey(videoId!),
    queryFn: () => videoApi.getContactTimestamps(videoId!),
    enabled: !!videoId && videoId > 0,
    staleTime: 1 * 60 * 1000, // 1 minute
  });

  return {
    contactTimestamps: query.data?.contact_timestamps ?? [],
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}
