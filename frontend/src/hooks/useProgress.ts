import { useQuery } from '@tanstack/react-query';
import { progressApi, ProgressResponse } from '../services/progressApi';

export const useProgress = (timePeriod: string = '30d', playerId?: number) => {
  const query = useQuery<ProgressResponse>({
    queryKey: ['progress', timePeriod, playerId],
    queryFn: () => progressApi.fetchProgress(timePeriod, playerId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  return {
    progress: query.data ?? null,
    loading: query.isLoading,
    error: query.error ? (query.error as Error).message : null,
  };
};
