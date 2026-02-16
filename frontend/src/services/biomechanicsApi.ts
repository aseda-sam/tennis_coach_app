import api from './api';
import { ServeBiomechanicsReport } from '../types/biomechanics';

export const biomechanicsApi = {
  getReport: (serveAttemptId: number): Promise<ServeBiomechanicsReport> =>
    api
      .get(`/serve-attempts/${serveAttemptId}/biomechanics`)
      .then((r) => r.data),

  computeReport: (serveAttemptId: number): Promise<ServeBiomechanicsReport> =>
    api
      .post(`/serve-attempts/${serveAttemptId}/biomechanics/compute`)
      .then((r) => r.data),

  getPlayerHistory: (
    playerId: number,
    limit: number = 20
  ): Promise<ServeBiomechanicsReport[]> =>
    api
      .get(`/players/${playerId}/biomechanics/history`, { params: { limit } })
      .then((r) => r.data),
};
