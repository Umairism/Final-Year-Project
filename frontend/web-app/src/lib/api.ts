import { API_CONFIG, API_ENDPOINTS } from './config';
import { VitalReading, PatientProfile, Alert, VitalStatus, PatientSources } from '@/types/vitals';
import { ApiResponse, ApiError, VitalReadingRequest, EmergencyRequest } from '@/types/api';
import { PatientProfileDto, PatientUpdateDto, toPatientProfile } from './profile';
import { getAccessToken } from './authToken';

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
      const token = getAccessToken();
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
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
      console.error('API request failed'); // Validation errors can contain private profile input.
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
    return toPatientProfile(await apiClient.get<PatientProfileDto>(API_ENDPOINTS.patientProfile(patientId)));
  },
  updateProfile: async (patientId: string, payload: PatientUpdateDto): Promise<PatientProfile> => {
    return toPatientProfile(await apiClient.put<PatientProfileDto>(API_ENDPOINTS.patient(patientId), payload));
  },
};

export interface AuthUser { id: string; email: string; full_name: string; patient_id: string | null; is_email_verified: boolean; }
export interface LoginResponse { access_token: string; token_type: 'bearer'; expires_in: number; user: AuthUser; }
export interface RegisterResponse { user: AuthUser; verification_required: boolean; email_delivery: { mode: string; sent: boolean }; }
export const authApi = {
  register: (payload: { email: string; password: string; full_name: string; age: number; blood_type?: string; gender?: string }) => apiClient.post<RegisterResponse>(API_ENDPOINTS.authRegister, payload),
  login: (payload: { email: string; password: string }) => apiClient.post<LoginResponse>(API_ENDPOINTS.authLogin, payload),
  verifyEmail: (token: string) => apiClient.post<{ verified: boolean; email: string }>(API_ENDPOINTS.authVerifyEmail, { token }),
  resendVerification: (email: string) => apiClient.post<{ message: string }>(API_ENDPOINTS.authResendVerification, { email }),
  me: () => apiClient.get<AuthUser>(API_ENDPOINTS.authMe),
};

export const getAuthErrorMessage = (error: unknown): string => {
  const e = error as { status?: number; detail?: unknown };
  const d = typeof e?.detail === 'object' && e.detail ? e.detail as { error?: string } : undefined;
  const code = d?.error;
  if (code === 'email_not_verified') return 'Please verify your email before signing in.';
  if (code === 'invalid_credentials') return 'Invalid email or password.';
  if (code === 'email_already_registered') return 'An account with this email already exists. Try logging in or resend verification.';
  if (code === 'email_delivery_failed') return 'Account created, but the verification email could not be sent. Use Resend.';
  if (code === 'auth_not_configured') return 'Authentication is not configured on the server.';
  if (code === 'invalid_or_expired_token') return 'This verification link is invalid or has expired.';
  if (e?.status === 422) return 'Please check the highlighted fields and try again.';
  return e?.status == null ? 'Cannot reach the HealSense backend.' : 'Authentication request failed.';
};

export interface AiProvidersResponse { openai: { configured: boolean; model: string }; gemini: { configured: boolean; model: string }; }
export interface PatientAssistantConversationTurn { role: 'user' | 'assistant'; content: string; }
export interface PatientAssistantRequest { patient_id: string; message: string; conversation: PatientAssistantConversationTurn[]; }
export interface PatientAssistantResponse { patient_id: string; answer: string; model: string; data_as_of: string; data_freshness_seconds: number; latest_status: string; is_simulated_data: boolean; disclaimer: string; }
export interface FusionRiskResponse { fused_decision?: { final_risk_level: string; confidence_score: number }; clinical_reasoning: string; }

export const getAiErrorMessage = (error: unknown): string => {
  const typed = error as { status?: number; detail?: unknown } | null;
  const detail = typed?.detail as { error?: string } | string | undefined;
  const code = typeof detail === 'object' && detail ? detail.error : undefined;
  if (typed?.status === 404 || code === 'patient_not_found') return 'Patient profile was not found.';
  if (typed?.status === 409 || code === 'no_vitals') return 'No readings are available for this patient yet.';
  if (typed?.status === 503 || code === 'gemini_not_configured') return 'Gemini is not configured for this backend.';
  if (typed?.status === 502 || code === 'gemini_upstream_error') return 'Gemini is temporarily unavailable. Please retry.';
  if (typed?.status === 422) return 'Please enter a valid question.';
  return 'Cannot reach the HealSense backend.';
};

export const aiApi = {
  getProviders: () => apiClient.get<AiProvidersResponse>(API_ENDPOINTS.aiProviders),
  askPatientAssistant: (request: PatientAssistantRequest) => apiClient.post<PatientAssistantResponse>(API_ENDPOINTS.patientAssistant, request),
  getFusionRisk: (patientId: string) => apiClient.get<FusionRiskResponse>(API_ENDPOINTS.fusionRisk(patientId)),
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
export interface AcknowledgeAlertResponse {
  alert_id: string;
  acknowledged: boolean;
  acknowledged_at: string;
  message: string;
}

export interface DismissAlertResponse {
  alert_id: string;
  dismissed: boolean;
  dismissed_at: string;
  message: string;
}

export const toAlert = (payload: Record<string, unknown>): Alert => ({
  id: String(payload.id),
  type: payload.severity === 'critical' || payload.type === 'critical' ? 'critical' : 'warning',
  vitalType: String(payload.vital_type ?? payload.vitalType ?? ''),
  value: payload.value == null ? null : Number(payload.value),
  threshold: String(payload.threshold ?? ''),
  timestamp: new Date(String(payload.timestamp)),
  acknowledged: Boolean(payload.acknowledged),
  dismissed: Boolean(payload.dismissed),
  message: typeof payload.message === 'string' ? payload.message : undefined,
});

export const alertsApi = {
  getAll: async (patientId: string): Promise<Alert[]> => {
    const payload = await apiClient.get<Record<string, unknown>[]>(API_ENDPOINTS.alerts(patientId));
    return payload.map(toAlert);
  },

  acknowledge: async (alertId: string): Promise<AcknowledgeAlertResponse> => {
    return apiClient.post<AcknowledgeAlertResponse>(API_ENDPOINTS.acknowledgeAlert(alertId), {});
  },

  dismiss: async (alertId: string): Promise<DismissAlertResponse> => {
    return apiClient.post<DismissAlertResponse>(API_ENDPOINTS.dismissAlert(alertId), {});
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
