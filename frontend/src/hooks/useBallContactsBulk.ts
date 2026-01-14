import { useQuery } from '@tanstack/react-query';
import { ballContactApi } from '../services/ballContactApi';
import type { BallContactsByVideo } from '../services/ballContactApi';

export const useBallContactsBulk = (videoIds: number[]) => {
  const key = [...videoIds].sort((a, b) => a - b).join(',');

  return useQuery<BallContactsByVideo>({
    queryKey: ['ball-contacts-bulk', key],
    queryFn: async () => {
      if (videoIds.length === 0) {
        return {};
      }

      try {
        return await ballContactApi.getContactsBulk(videoIds);
      } catch (error) {
        console.error('Error fetching bulk ball contacts:', error);
        return {};
      }
    },
    enabled: videoIds.length > 0,
    staleTime: 2 * 60 * 1000,
  });
};
