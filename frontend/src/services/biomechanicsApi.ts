import api from './api';
import { ServeBiomechanicsReport } from '../types/biomechanics';

export const biomechanicsApi = {
  getReport: (serveWindowId: number): Promise<ServeBiomechanicsReport> =>
    api.get(`/serve-windows/${serveWindowId}/biomechanics`).then((r) => r.data),

  computeReport: (serveWindowId: number): Promise<ServeBiomechanicsReport> =>
    api
      .post(`/serve-windows/${serveWindowId}/biomechanics/compute`)
      .then((r) => r.data),

  getPlayerHistory: (
    playerId: number,
    limit: number = 20
  ): Promise<ServeBiomechanicsReport[]> =>
    api
      .get(`/players/${playerId}/biomechanics/history`, { params: { limit } })
      .then((r) => r.data),
};
