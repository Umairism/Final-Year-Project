import { useState, useEffect, useCallback, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { vitalsApi, alertsApi, toVitalReading } from '@/lib/api';
import { API_CONFIG } from '@/lib/config';
import { VitalReading, VitalStatus, DEFAULT_THRESHOLDS, Alert } from '@/types/vitals';
import { useVitalsWebSocket } from '@/hooks/useWebSocket';
import { AlertActions, visibleAlerts } from '@/lib/alerts';
import { mergeVitalReadings } from '@/lib/vitalsReadings';

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
  value: number | null
): VitalStatus => {
  if (value == null) return 'normal';
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
    useMockData ? generateHistoricalData(60).map(r => ({...r, dataOrigin:'simulated'})) : []
  );
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isConnected, setIsConnected] = useState(useMockData);
  const actionState = useRef<{ patientId: string; actions: AlertActions }>({ patientId, actions: new Map() });
  if (actionState.current.patientId !== patientId) {
    actionState.current = { patientId, actions: new Map() };
  }
  const confirmedActions = actionState.current.actions;

  // Fetch historical vitals from API
  const { data: historicalData, isLoading: isLoadingHistory, isError: isHistoryError, refetch: refetchHistory } = useQuery<VitalReading[]>({
    queryKey: ['vitals-history', patientId],
    queryFn: () => vitalsApi.getHistory(patientId, 1440),
    enabled: !useMockData && Boolean(patientId),
    refetchInterval: 60000, // Refetch every minute
  });

  // Fetch alerts from API
  const { data: apiAlerts } = useQuery<Alert[]>({
    queryKey: ['alerts', patientId],
    queryFn: () => alertsApi.getAll(patientId),
    enabled: !useMockData && Boolean(patientId),
    refetchInterval: 10000, // Refetch every 10 seconds
  });

  // Update readings when historical data is fetched
  useEffect(() => {
    if (historicalData && !useMockData) {
      setReadings((prev) => mergeVitalReadings(prev, historicalData));
      setIsConnected(true);
    }
  }, [historicalData, useMockData]);

  // Update alerts when API alerts are fetched
  useEffect(() => {
    if (apiAlerts && !useMockData) {
      setAlerts(visibleAlerts(apiAlerts, confirmedActions));
    }
  }, [apiAlerts, useMockData, confirmedActions]);

  const checkForAlerts = useCallback((reading: VitalReading) => {
    if (!useMockData) return;
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
  }, [useMockData]);

  const currentReading = readings[readings.length - 1];

  const handleVitalUpdate = useCallback((event: any) => {
    const payload = event?.payload;
    if (!payload) return;
    if (event.event_type?.startsWith('alert.')) {
      if (useMockData) return;
      if (payload.alert_id && (event.event_type === 'alert.acknowledged' || event.event_type === 'alert.dismissed')) {
        const previous = confirmedActions.get(payload.alert_id);
        confirmedActions.set(payload.alert_id, {
          ...previous,
          ...(payload.acknowledged === true ? { acknowledged: true } : {}),
          ...(payload.dismissed === true ? { dismissed: true } : {}),
        });
        setAlerts(prev => visibleAlerts(prev, confirmedActions));
      }
      return;
    }
    const reading = toVitalReading(payload?.vital ?? payload);
    if (!reading.heartRate && !reading.spo2 && !reading.temperature) return;
    setReadings((prev) => mergeVitalReadings(prev, reading));
    checkForAlerts(reading);
  }, [checkForAlerts, useMockData, confirmedActions]);

  const {
    isConnected: isRealtimeConnected,
  } = useVitalsWebSocket(patientId, handleVitalUpdate, Boolean(patientId));

  const acknowledgeAlert = useCallback(async (alertId: string): Promise<boolean> => {
    if (!useMockData) {
      try {
        const result = await alertsApi.acknowledge(alertId);
        if (!result.acknowledged) return false;
      } catch (error) {
        console.error('Failed to acknowledge alert:', error);
        return false;
      }
    }
    
    confirmedActions.set(alertId, { ...confirmedActions.get(alertId), acknowledged: true });
    setAlerts(prev => visibleAlerts(prev, confirmedActions));
    return true;
  }, [useMockData, confirmedActions]);

  const dismissAlert = useCallback(async (alertId: string): Promise<boolean> => {
    if (!useMockData) {
      try {
        const result = await alertsApi.dismiss(alertId);
        if (!result.dismissed) return false;
      } catch (error) {
        console.error('Failed to dismiss alert:', error);
        return false;
      }
    }

    confirmedActions.set(alertId, { ...confirmedActions.get(alertId), dismissed: true });
    setAlerts(prev => visibleAlerts(prev, confirmedActions));
    return true;
  }, [useMockData, confirmedActions]);

  // Periodic updates for mock data only
  useEffect(() => {
    if (!useMockData) return;

    const interval = setInterval(() => {
      setReadings((prev) => {
        const newReading = generateVitalReading(prev[prev.length - 1]);
        checkForAlerts(newReading);
        return [...prev.slice(1), newReading];
      });
    }, API_CONFIG.pollingInterval);

    return () => clearInterval(interval);
  }, [useMockData, checkForAlerts]);

  return {
    readings,
    currentReading,
    alerts,
    isConnected,
    isRealtimeConnected,
    acknowledgeAlert,
    dismissAlert,
    refetchHistory,
    isLoadingHistory,
    isHistoryError,
  };
};
