import { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { vitalsApi, alertsApi } from '@/lib/api';
import { API_CONFIG } from '@/lib/config';
import { VitalReading, VitalStatus, DEFAULT_THRESHOLDS, Alert } from '@/types/vitals';
import { useVitalsWebSocket } from '@/hooks/useWebSocket';

const generateId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  return `vital_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
};

// Mock data generators (only used when useMockData is true)
const generateVitalReading = (prevReading?: VitalReading): VitalReading => {
  const vary = (value: number, range: number) => {
    return Math.max(0, value + (Math.random() - 0.5) * range);
  };

  const base = prevReading || {
    heartRate: 72,
    spo2: 98,
    temperature: 36.6,
    systolic: 120,
    diastolic: 80,
    respiratoryRate: 16,
  };

  return {
    id: generateId(),
    timestamp: new Date(),
    heartRate: Math.round(vary(base.heartRate, 8)),
    spo2: Math.min(100, Math.max(88, Math.round(vary(base.spo2, 2)))),
    temperature: Number(vary(base.temperature, 0.3).toFixed(1)),
    systolic: Math.round(vary(base.systolic, 10)),
    diastolic: Math.round(vary(base.diastolic, 6)),
    respiratoryRate: Math.round(vary(base.respiratoryRate, 3)),
  };
};

// Generate historical data for charts
const generateHistoricalData = (minutes: number): VitalReading[] => {
  const data: VitalReading[] = [];
  let current: VitalReading | undefined;

  for (let i = minutes; i >= 0; i--) {
    current = generateVitalReading(current);
    current.timestamp = new Date(Date.now() - i * 60 * 1000);
    data.push(current);
  }

  return data;
};

export const getVitalStatus = (
  vital: keyof typeof DEFAULT_THRESHOLDS,
  value: number
): VitalStatus => {
  const thresholds = DEFAULT_THRESHOLDS[vital];

  if (vital === 'spo2') {
    const spo2Thresholds = thresholds as typeof DEFAULT_THRESHOLDS.spo2;
    if (value < spo2Thresholds.min) return 'critical';
    if (value < spo2Thresholds.warningMin) return 'warning';
    return 'normal';
  }

  const rangeThresholds = thresholds as typeof DEFAULT_THRESHOLDS.heartRate;
  if (value < rangeThresholds.min || value > rangeThresholds.max) return 'critical';
  if (value < rangeThresholds.warningMin || value > rangeThresholds.warningMax) return 'warning';
  return 'normal';
};

interface UseVitalsOptions {
  patientId: string;
  useMockData?: boolean;
}

export const useVitals = ({ patientId, useMockData = API_CONFIG.useMockData }: UseVitalsOptions) => {
  const [readings, setReadings] = useState<VitalReading[]>(() => 
    useMockData ? generateHistoricalData(60) : []
  );
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isConnected, setIsConnected] = useState(true);

  const toVitalReading = useCallback((payload: Record<string, unknown>): VitalReading => {
    const now = new Date();
    return {
      id: String(payload.id ?? generateId()),
      timestamp: new Date(String(payload.timestamp ?? now.toISOString())),
      heartRate: Number(payload.heart_rate ?? payload.heartRate ?? 0),
      spo2: Number(payload.spo2 ?? 0),
      temperature: Number(payload.temperature ?? 0),
      systolic: Number(payload.systolic_bp ?? payload.systolic ?? 0),
      diastolic: Number(payload.diastolic_bp ?? payload.diastolic ?? 0),
      respiratoryRate: Number(payload.respiratory_rate ?? payload.respiratoryRate ?? 0),
    };
  }, []);

  // Fetch historical vitals from API
  const { data: historicalData } = useQuery<VitalReading[]>({
    queryKey: ['vitals-history', patientId],
    queryFn: () => vitalsApi.getHistory(patientId, 60),
    enabled: !useMockData,
    refetchInterval: 60000, // Refetch every minute
  });

  // Fetch alerts from API
  const { data: apiAlerts } = useQuery<Alert[]>({
    queryKey: ['alerts', patientId],
    queryFn: () => alertsApi.getAll(patientId),
    enabled: !useMockData,
    refetchInterval: 10000, // Refetch every 10 seconds
  });

  // Update readings when historical data is fetched
  useEffect(() => {
    if (historicalData && !useMockData) {
      setReadings(historicalData);
    }
  }, [historicalData, useMockData]);

  // Update alerts when API alerts are fetched
  useEffect(() => {
    if (apiAlerts && !useMockData) {
      setAlerts(apiAlerts);
    }
  }, [apiAlerts, useMockData]);

  const checkForAlerts = useCallback((reading: VitalReading) => {
    const vitalTypes: (keyof typeof DEFAULT_THRESHOLDS)[] = [
      'heartRate', 'spo2', 'temperature', 'systolic', 'diastolic', 'respiratoryRate'
    ];

    const newAlerts: Alert[] = [];

    vitalTypes.forEach((vital) => {
      const value = reading[vital];
      const status = getVitalStatus(vital, value);

      if (status !== 'normal') {
        newAlerts.push({
          id: generateId(),
          type: status,
          vitalType: vital,
          value,
          threshold: status === 'critical' ? 'Critical' : 'Warning',
          timestamp: new Date(),
          acknowledged: false,
        });
      }
    });

    if (newAlerts.length > 0) {
      setAlerts((prev) => [...newAlerts, ...prev].slice(0, 50));
    }
  }, []);

  const currentReading = readings[readings.length - 1];

  const {
    isConnected: isRealtimeConnected,
  } = useVitalsWebSocket(patientId, (event: any) => {
    const payload = event?.payload;
    if (!payload) return;

    const vitalPayload = payload?.vital ?? payload;
    const reading = toVitalReading(vitalPayload);
    if (!reading.heartRate && !reading.spo2 && !reading.temperature) return;

    setReadings((prev) => [...prev, reading].slice(-60));
    checkForAlerts(reading);
  });

  const acknowledgeAlert = useCallback(async (alertId: string) => {
    if (!useMockData) {
      try {
        await alertsApi.acknowledge(alertId);
      } catch (error) {
        console.error('Failed to acknowledge alert:', error);
      }
    }
    
    setAlerts((prev) =>
      prev.map((alert) =>
        alert.id === alertId ? { ...alert, acknowledged: true } : alert
      )
    );
  }, [useMockData]);

  const dismissAlert = useCallback(async (alertId: string) => {
    if (!useMockData) {
      try {
        await alertsApi.dismiss(alertId);
      } catch (error) {
        console.error('Failed to dismiss alert:', error);
      }
    }
    
    setAlerts((prev) => prev.filter((alert) => alert.id !== alertId));
  }, [useMockData]);

  // Real-time updates via polling (for mock data)
  useEffect(() => {
    if (!useMockData) return;

    const interval = setInterval(() => {
      const newReading = generateVitalReading(readings[readings.length - 1]);
      
      setReadings((prev) => {
        const updated = [...prev, newReading];
        return updated.slice(-60);
      });

      checkForAlerts(newReading);
    }, API_CONFIG.pollingInterval);

    return () => clearInterval(interval);
  }, [readings, checkForAlerts, useMockData]);

  // Real-time updates via API polling (when backend is ready)
  useEffect(() => {
    if (useMockData) return;

    const interval = setInterval(async () => {
      if (isRealtimeConnected) {
        setIsConnected(true);
        return;
      }

      try {
        const latestReading = await vitalsApi.getLatest(patientId);
        setReadings((prev) => {
          const updated = [...prev, latestReading];
          return updated.slice(-60);
        });
        checkForAlerts(latestReading);
        setIsConnected(true);
      } catch (error) {
        console.error('Failed to fetch latest vitals:', error);
        setIsConnected(false);
      }
    }, API_CONFIG.pollingInterval);

    return () => clearInterval(interval);
  }, [patientId, checkForAlerts, useMockData, isRealtimeConnected]);

  // Simulate connection status (for mock data only)
  useEffect(() => {
    if (!useMockData) return;
    const interval = setInterval(() => {
      if (Math.random() < 0.05) {
        setIsConnected(false);
        setTimeout(() => setIsConnected(true), 2000);
      }
    }, 10000);

    return () => clearInterval(interval);
  }, [useMockData]);

  return {
    currentReading,
    readings,
    alerts,
    isConnected,
    isRealtimeConnected,
    acknowledgeAlert,
    dismissAlert,
  };
};
