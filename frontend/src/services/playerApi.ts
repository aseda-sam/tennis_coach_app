import api from './api';

export interface PlayerProfileUpdate {
  name?: string;
  dominant_hand?: string;
  backhand_style?: string;
  notes?: string;
}

export interface PlayerInfo {
  id: number;
  name: string;
  dominant_hand: string;
  backhand_style?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export const playerApi = {
  upsertMe: async (profile: PlayerProfileUpdate): Promise<PlayerInfo> => {
    const response = await api.put<PlayerInfo>('/players/me', profile);
    return response.data;
  },
};
