export type BpSource = 'manual_entry' | 'ble_cuff' | 'hardware_uart' | 'none';
export type HealthStatus = 'normal' | 'warning' | 'critical';

export interface TelemetryPayload {
  device_id: string;
  patient_id: string;
  heart_rate: number;
  spo2: number;
  temperature: number;
  systolic_bp?: number | null;
  diastolic_bp?: number | null;
  bp_source?: BpSource;
  delayed_sync?: boolean;
  timestamp?: string;
  data_origin?: 'device' | 'simulated' | string;
}

export interface FusedDecision {
  final_risk_level: HealthStatus;
  confidence_score?: number;
  deterministic_flags?: string[];
  ml_risk_probability?: number | null;
  fusion_method?: string;
}

export interface TelemetryResponse {
  success: boolean;
  message: string;
  vital_id: string;
  patient_id: string;
  device_id: string;
  status: HealthStatus;
  fused_decision: FusedDecision;
  explanation?: string | null;
}

export interface SerializedVital {
  id: string;
  patient_id: string;
  device_id?: string | null;
  heart_rate: number;
  spo2: number;
  temperature: number;
  systolic_bp?: number | null;
  diastolic_bp?: number | null;
  respiratory_rate?: number | null;
  bp_source?: BpSource | string | null;
  delayed_sync?: boolean;
  timestamp?: string | null;
  status?: HealthStatus | string | null;
  risk_score?: number | null;
  prediction_confidence?: number | null;
  full_probability_distribution?: Record<string, number> | null;
  model_version?: string | null;
  data_origin?: string;
}

export interface PatientVitalsCreatedPayload {
  vital: SerializedVital;
  device_id?: string | null;
  fused_decision?: FusedDecision;
}

export interface PatientVitalsCreatedEvent {
  event_type: 'patient.vitals.created' | string;
  timestamp: string;
  patient_id: string;
  payload: PatientVitalsCreatedPayload;
}

export interface VitalReading {
  id: string;
  timestamp: string | Date;
  heartRate: number;
  spo2: number;
  temperature: number;
  systolic?: number | null;
  diastolic?: number | null;
  bpSource?: BpSource;
  delayedSync?: boolean;
  status?: HealthStatus;
  riskScore?: number;
  explanation?: string;
}

export interface DeviceStatus {
  device_id: string;
  patient_id?: string | null;
  device_type: string;
  connected: boolean;
  battery_level?: number | null;
  signal_strength?: number | null;
  last_heartbeat?: string | null;
}
