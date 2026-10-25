export type VitalStatus = 'normal' | 'warning' | 'critical';

export interface VitalReading {
  id: string;
  timestamp: Date;
  heartRate: number;
  spo2: number;
  temperature: number;
  systolic: number | null;
  diastolic: number | null;
  respiratoryRate: number | null;
  bpSource?: string;
  status?: VitalStatus;
  riskScore?: number | null;
  predictionConfidence?: number | null;
  probabilityDistribution?: Record<string, number> | null;
  delayedSync?: boolean;
  dataOrigin?: 'device' | 'mobile_app' | 'manual' | 'simulated' | 'seed' | string;
}

export interface PatientDataSource { deviceId: string; deviceType?: string; connected: boolean; enabled: boolean; presenceStatus?: string; isOnline: boolean; lastSeen: Date | null; lastSeenSecondsAgo: number | null; batteryLevel?: number | null; }
export interface PatientSources { patientId: string; dataSources: PatientDataSource[]; primarySource: string | null; totalDevices: number; fetchedAt: number; }

export interface VitalThresholds {
  heartRate: { min: number; max: number; warningMin: number; warningMax: number };
  spo2: { min: number; warningMin: number };
  temperature: { min: number; max: number; warningMin: number; warningMax: number };
  systolic: { min: number; max: number; warningMin: number; warningMax: number };
  diastolic: { min: number; max: number; warningMin: number; warningMax: number };
  respiratoryRate: { min: number; max: number; warningMin: number; warningMax: number };
}

export interface EmergencyContact {
  name: string;
  phone: string;
  relation: string;
  type: 'doctor' | 'family' | 'other';
}

export interface PatientProfile {
  id: string;
  name: string;
  firstName: string;
  lastName: string;
  email?: string | null;
  age: number;
  gender: string;
  bloodType: string;
  avatar?: string;
  conditions: string[];
  medications: string[];
  diabetes: 'true' | 'false' | 'unknown';
  smokingStatus: 'non_smoker' | 'former_smoker' | 'current_smoker' | 'unknown';
  emergencyContacts: EmergencyContact[];
}

export interface Alert {
  id: string;
  type: 'warning' | 'critical';
  vitalType: string;
  value: number | null;
  threshold: string;
  timestamp: Date;
  acknowledged: boolean;
  dismissed?: boolean;
  message?: string;
}

export const DEFAULT_THRESHOLDS: VitalThresholds = {
  heartRate: { min: 40, max: 120, warningMin: 50, warningMax: 100 },
  spo2: { min: 90, warningMin: 95 },
  temperature: { min: 35, max: 39.5, warningMin: 36, warningMax: 37.5 },
  systolic: { min: 80, max: 180, warningMin: 100, warningMax: 140 },
  diastolic: { min: 50, max: 110, warningMin: 60, warningMax: 90 },
  respiratoryRate: { min: 8, max: 30, warningMin: 12, warningMax: 20 },
};
