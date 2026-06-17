// API Configuration
export const API_CONFIG = {
  baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1',
  wsUrl: import.meta.env.VITE_WS_URL || 'ws://localhost:5000',
  pollingInterval: Number(import.meta.env.VITE_POLLING_INTERVAL) || 5000,
  useMockData: import.meta.env.VITE_USE_MOCK_DATA !== 'false', // Default to true
};

// API Endpoints
export const API_ENDPOINTS = {
  // Patient endpoints
  patient: (id: string) => `/patients/${id}`,
  patientProfile: (id: string) => `/patients/${id}/profile`,
  
  // Vitals endpoints
  vitals: (patientId: string) => `/patients/${patientId}/vitals`,
  latestVital: (patientId: string) => `/patients/${patientId}/vitals/latest`,
  vitalHistory: (patientId: string, minutes: number) => 
    `/patients/${patientId}/vitals/history?minutes=${minutes}`,
  
  // Alerts endpoints
  alerts: (patientId: string) => `/patients/${patientId}/alerts`,
  acknowledgeAlert: (alertId: string) => `/alerts/${alertId}/acknowledge`,
  dismissAlert: (alertId: string) => `/alerts/${alertId}/dismiss`,
  
  // Emergency
  emergency: (patientId: string) => `/patients/${patientId}/emergency`,
  
  // Device/IoT
  deviceStatus: (deviceId: string) => `/devices/${deviceId}/status`,
  deviceConnect: (deviceId: string) => `/devices/${deviceId}/connect`,
  patientDeviceSources: (patientId: string) => `/devices/patient/${patientId}/sources`,
};

// WebSocket Topics
export const WS_TOPICS = {
  vitals: (patientId: string) => `ws/patients/${patientId}`,
  alerts: (patientId: string) => `ws/patients/${patientId}`,
  device: (deviceId: string) => `ws/devices/${deviceId}`,
};
