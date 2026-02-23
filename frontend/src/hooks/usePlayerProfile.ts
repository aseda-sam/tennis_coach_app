import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { playerApi } from '../services/playerApi';
import { PlayerInfo, PlayerProfileUpdate } from '../types/player';
import { useAuth } from './useAuth';

export const usePlayerProfile = () => {
  const { user } = useAuth();

  return useQuery<PlayerInfo, Error>({
    queryKey: ['player-profile', user?.id],
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
      queryClient.invalidateQueries({ queryKey: ['player-profile'] });
    },
  });
};
