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
