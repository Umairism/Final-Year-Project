export type VitalStatus = 'normal' | 'warning' | 'critical';

export interface VitalReading {
  id: string;
  timestamp: Date;
  heartRate: number;
  spo2: number;
  temperature: number;
  systolic: number;
  diastolic: number;
  respiratoryRate: number;
}

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
  type: 'doctor' | 'family';
}

export interface PatientProfile {
  id: string;
  name: string;
  age: number;
  gender: string;
  bloodType: string;
  avatar?: string;
  conditions: string[];
  medications: string[];
  emergencyContacts: EmergencyContact[];
}

export interface Alert {
  id: string;
  type: 'warning' | 'critical';
  vitalType: string;
  value: number;
  threshold: string;
  timestamp: Date;
  acknowledged: boolean;
}

export const DEFAULT_THRESHOLDS: VitalThresholds = {
  heartRate: { min: 40, max: 120, warningMin: 50, warningMax: 100 },
  spo2: { min: 90, warningMin: 95 },
  temperature: { min: 35, max: 39.5, warningMin: 36, warningMax: 37.5 },
  systolic: { min: 80, max: 180, warningMin: 100, warningMax: 140 },
  diastolic: { min: 50, max: 110, warningMin: 60, warningMax: 90 },
  respiratoryRate: { min: 8, max: 30, warningMin: 12, warningMax: 20 },
};
