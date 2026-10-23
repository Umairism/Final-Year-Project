import { API_CONFIG, API_ENDPOINTS } from './config';
import { VitalReading, PatientProfile, Alert, VitalStatus, PatientSources } from '@/types/vitals';
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
        const error: ApiError & { detail?: unknown } = await response.json();
        const detail = error.detail;
        const message = typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : error.message || 'API request failed';
        throw Object.assign(new Error(message), { status: response.status, detail });
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

export const toVitalReading = (payload: Record<string, unknown>): VitalReading => ({
  id: String(payload.id ?? crypto.randomUUID()),
  timestamp: new Date(String(payload.timestamp)),
  heartRate: Number(payload.heart_rate ?? 0),
  spo2: Number(payload.spo2 ?? 0),
  temperature: Number(payload.temperature ?? 0),
  systolic: payload.systolic_bp == null ? null : Number(payload.systolic_bp),
  diastolic: payload.diastolic_bp == null ? null : Number(payload.diastolic_bp),
  respiratoryRate: payload.respiratory_rate == null ? null : Number(payload.respiratory_rate),
  bpSource: payload.bp_source as string | undefined,
  status: payload.status as VitalStatus | undefined,
  riskScore: payload.risk_score == null ? null : Number(payload.risk_score),
  predictionConfidence: payload.prediction_confidence == null ? null : Number(payload.prediction_confidence),
  probabilityDistribution: payload.full_probability_distribution as Record<string, number> | null | undefined,
  delayedSync: Boolean(payload.delayed_sync ?? false),
  dataOrigin: String(payload.data_origin ?? payload.dataOrigin ?? 'device'),
});

// Patient API
export const patientApi = {
  getProfile: async (patientId: string): Promise<PatientProfile> => {
    return apiClient.get<PatientProfile>(API_ENDPOINTS.patientProfile(patientId));
  },
};

// Vitals API
export const vitalsApi = {
  getLatest: async (patientId: string): Promise<VitalReading> => {
    const payload = await apiClient.get<Record<string, unknown>>(API_ENDPOINTS.latestVital(patientId));
    return toVitalReading(payload);
  },

  getHistory: async (patientId: string, minutes: number = 1440): Promise<VitalReading[]> => {
    const payload = await apiClient.get<Record<string, unknown>[]>(API_ENDPOINTS.vitalHistory(patientId, minutes));
    return payload.map(toVitalReading).sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
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
  trigger: async (request: EmergencyRequest): Promise<{ emergency_id: string; patient_id: string; triggered_at: string; status: string; message: string }> => {
    return apiClient.post(API_ENDPOINTS.emergency(request.patientId), request);
  },
};

// Device API
export const deviceApi = {
  getStatus: async (deviceId: string): Promise<{ connected: boolean; lastSeen: Date }> => {
    return apiClient.get<{ connected: boolean; lastSeen: Date }>(
      API_ENDPOINTS.deviceStatus(deviceId)
    );
  },

  getPatientSources: async (patientId: string): Promise<PatientSources> => {
    const raw = await apiClient.get<any>(API_ENDPOINTS.patientDeviceSources(patientId));
    return { patientId: raw.patient_id, primarySource: raw.primary_source, totalDevices: raw.total_devices ?? 0, fetchedAt: Date.now(), dataSources: (raw.data_sources ?? []).map((d:any) => ({ deviceId:d.device_id, deviceType:d.device_type, connected:Boolean(d.connected), enabled:Boolean(d.enabled ?? d.connected), presenceStatus:d.presence_status, isOnline:Boolean(d.is_online), lastSeen:d.last_seen ? new Date(d.last_seen) : null, lastSeenSecondsAgo:d.last_seen_seconds_ago ?? null, batteryLevel:d.battery_level ?? null })) };
  },

  connect: async (deviceId: string, patientId: string): Promise<void> => {
    return apiClient.post<void>(`${API_ENDPOINTS.deviceConnect(deviceId)}?patient_id=${encodeURIComponent(patientId)}`, {});
  },
  disconnect: async (deviceId: string): Promise<void> => {
    return apiClient.post<void>(API_ENDPOINTS.deviceDisconnect(deviceId), {});
  },
};

export interface BpEntryPayload {
  systolic_bp: number;
  diastolic_bp: number;
  pulse?: number;
  measured_at?: string;
  note?: string;
  bp_source: 'manual_entry';
  heart_rate?: number;
  spo2?: number;
  temperature?: number;
}

export interface BpEntryResponse {
  success: boolean;
  attached: boolean;
  vital_id: string;
  patient_id: string;
  systolic_bp: number;
  diastolic_bp: number;
  pulse?: number | null;
  bp_source: string;
  category: string;
  triggered_rules: string[];
  status: string;
  alert_id?: string | null;
  message: string;
}

export const bpApi = {
  record: (patientId: string, payload: BpEntryPayload) =>
    apiClient.post<BpEntryResponse>(API_ENDPOINTS.bp(patientId), payload),
  history: (patientId: string, limit = 5) =>
    apiClient.get<Array<{ timestamp?: string; systolic_bp: number; diastolic_bp: number; status?: string }>>(
      API_ENDPOINTS.bpHistory(patientId, limit)
    ),
};
