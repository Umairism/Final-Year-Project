import { API_CONFIG, API_ENDPOINTS } from './config';
import { VitalReading, PatientProfile, Alert } from '@/types/vitals';
import { ApiResponse, ApiError, VitalReadingRequest, EmergencyRequest } from '@/types/api';

// API Client with error handling
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      });

      if (!response.ok) {
        const error: ApiError = await response.json();
        throw new Error(error.message || 'API request failed');
      }

      const payload = await response.json();
      if (
        payload &&
        typeof payload === 'object' &&
        'data' in payload &&
        'success' in payload
      ) {
        return (payload as ApiResponse<T>).data;
      }

      return payload as T;
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, data: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async put<T>(endpoint: string, data: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

// Initialize API client
const apiClient = new ApiClient(API_CONFIG.baseUrl);

// Patient API
export const patientApi = {
  getProfile: async (patientId: string): Promise<PatientProfile> => {
    return apiClient.get<PatientProfile>(API_ENDPOINTS.patientProfile(patientId));
  },
};

// Vitals API
export const vitalsApi = {
  getLatest: async (patientId: string): Promise<VitalReading> => {
    return apiClient.get<VitalReading>(API_ENDPOINTS.latestVital(patientId));
  },

  getHistory: async (patientId: string, minutes: number = 60): Promise<VitalReading[]> => {
    return apiClient.get<VitalReading[]>(API_ENDPOINTS.vitalHistory(patientId, minutes));
  },

  submit: async (reading: VitalReadingRequest): Promise<VitalReading> => {
    return apiClient.post<VitalReading>(
      API_ENDPOINTS.vitals(reading.patientId),
      reading
    );
  },
};

// Alerts API
export const alertsApi = {
  getAll: async (patientId: string): Promise<Alert[]> => {
    return apiClient.get<Alert[]>(API_ENDPOINTS.alerts(patientId));
  },

  acknowledge: async (alertId: string): Promise<Alert> => {
    return apiClient.post<Alert>(API_ENDPOINTS.acknowledgeAlert(alertId), {});
  },

  dismiss: async (alertId: string): Promise<void> => {
    return apiClient.delete<void>(API_ENDPOINTS.dismissAlert(alertId));
  },
};

// Emergency API
export const emergencyApi = {
  trigger: async (request: EmergencyRequest): Promise<void> => {
    return apiClient.post<void>(API_ENDPOINTS.emergency(request.patientId), request);
  },
};

// Device API
export const deviceApi = {
  getStatus: async (deviceId: string): Promise<{ connected: boolean; lastSeen: Date }> => {
    return apiClient.get<{ connected: boolean; lastSeen: Date }>(
      API_ENDPOINTS.deviceStatus(deviceId)
    );
  },

  getPatientSources: async (
    patientId: string
  ): Promise<{
    patient_id: string;
    data_sources: Array<{ device_id: string; connected: boolean }>;
    primary_source: string | null;
    total_devices: number;
  }> => {
    return apiClient.get(API_ENDPOINTS.patientDeviceSources(patientId));
  },

  connect: async (deviceId: string): Promise<void> => {
    return apiClient.post<void>(API_ENDPOINTS.deviceConnect(deviceId), {});
  },
};
