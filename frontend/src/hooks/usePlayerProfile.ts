import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { playerApi, PlayerInfo, PlayerProfileUpdate } from '../services/playerApi';
import { useAuth } from './useAuth';

export const usePlayerProfile = () => {
  const { user } = useAuth();

  return useQuery<PlayerInfo, Error>({
    queryKey: ['playerProfile', user?.id],
    queryFn: playerApi.getMe,
    enabled: !!user,
    retry: 1,
  });
};

export const useUpsertPlayerProfile = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (profile: PlayerProfileUpdate) => playerApi.upsertMe(profile),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['playerProfile'] });
    },
  });
};
