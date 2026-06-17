// API Response Types
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  timestamp: string;
}

export interface ApiError {
  success: false;
  error: string;
  message: string;
  statusCode: number;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  pagination: {
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
  };
}

// API Request Types
export interface VitalReadingRequest {
  patientId: string;
  heartRate: number;
  spo2: number;
  temperature: number;
  systolic: number;
  diastolic: number;
  respiratoryRate: number;
  deviceId?: string;
}

export interface EmergencyRequest {
  patientId: string;
  reason: string;
  location?: {
    latitude: number;
    longitude: number;
  };
}

export interface AlertAcknowledgement {
  alertId: string;
  acknowledgedBy: string;
  notes?: string;
}
