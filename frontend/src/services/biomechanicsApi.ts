import api, { API_BASE_URL } from './api';
import {
  CoachingFeedbackResponse,
  CoachingNoteResponse,
  ServeBiomechanicsReport,
} from '../types/biomechanics';
import { getAuthHeaders } from '../utils/authInterceptor';

export const biomechanicsApi = {
  getReport: (serveWindowId: number): Promise<ServeBiomechanicsReport> =>
    api.get(`/serve-windows/${serveWindowId}/biomechanics`).then((r) => r.data),

  getFrame: async (serveWindowId: number, ktp: string): Promise<Blob> => {
    const authHeaders = await getAuthHeaders();
    const url = `${API_BASE_URL}/serve-windows/${serveWindowId}/frame?ktp=${encodeURIComponent(ktp)}`;
    const response = await fetch(url, { headers: authHeaders });
    if (!response.ok) throw new Error(`Frame fetch failed: ${response.status}`);
    return response.blob();
  },

  getCoachingFeedback: (
    serveWindowId: number
  ): Promise<CoachingFeedbackResponse> =>
    api.get(`/serve-windows/${serveWindowId}/coaching`).then((r) => r.data),

  getCoachingNotes: (serveWindowId: number): Promise<CoachingNoteResponse[]> =>
    api
      .get(`/serve-windows/${serveWindowId}/coaching/notes`)
      .then((r) => r.data),

  saveCoachingNote: (
    serveWindowId: number,
    note: string
  ): Promise<CoachingNoteResponse> =>
    api
      .post(`/serve-windows/${serveWindowId}/coaching/notes`, { note })
      .then((r) => r.data),

  getPlayerHistory: (
    playerId: number,
    limit?: number
  ): Promise<ServeBiomechanicsReport[]> =>
    api
      .get(`/players/${playerId}/biomechanics/history`, {
        params: { limit },
      })
      .then((r) => r.data),
};
