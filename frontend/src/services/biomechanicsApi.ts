import api from './api';
import { ServeBiomechanicsReport } from '../types/biomechanics';

export const biomechanicsApi = {
  getReport: (serveWindowId: number): Promise<ServeBiomechanicsReport> =>
    api.get(`/serve-windows/${serveWindowId}/biomechanics`).then((r) => r.data),
};
