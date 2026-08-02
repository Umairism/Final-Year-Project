import { apiClient } from './apiClient';
import { TelemetryPayload, TelemetryResponse, VitalReading } from '@/types/telemetry';

export const telemetryService = {
  /**
   * Submit telemetry directly to POST /api/v1/telemetry
   * Supports hardware device authentication header X-Device-API-Key
   */
  submitTelemetry: async (
    payload: TelemetryPayload,
    apiKey?: string
  ): Promise<TelemetryResponse> => {
    const headers: Record<string, string> = {};
    if (apiKey) {
      headers['X-Device-API-Key'] = apiKey;
    }
    return apiClient.post<TelemetryResponse>('/api/v1/telemetry', payload, headers);
  },

  /**
   * Fetch patient's latest vital signs
   */
  getLatestVitals: async (patientId: string): Promise<VitalReading> => {
    return apiClient.get<VitalReading>(`/api/v1/patients/${patientId}/vitals/latest`);
  },

  /**
   * Fetch patient hybrid risk fusion evaluation
   */
  getFusionRisk: async (patientId: string): Promise<any> => {
    return apiClient.get(`/api/v1/patients/${patientId}/fusion_risk`);
  }
};
