import type { PlayerInfo, PlayerProfileUpdate } from '../types/player';
import api from './api';

export type { PlayerInfo, PlayerProfileUpdate } from '../types/player';

export const playerApi = {
  getMe: async (): Promise<PlayerInfo> => {
    const response = await api.get<PlayerInfo>('/players/me');
    return response.data;
  },
  upsertMe: async (profile: PlayerProfileUpdate): Promise<PlayerInfo> => {
    const response = await api.put<PlayerInfo>('/players/me', profile);
    return response.data;
  },
};
