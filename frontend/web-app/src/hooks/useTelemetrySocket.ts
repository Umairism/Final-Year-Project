import { useEffect, useState, useCallback, useRef } from 'react';
import { API_CONFIG } from '@/lib/config';

export interface TelemetryIngestedEvent {
  event: string;
  patient_id: string;
  vital_id?: string;
  heart_rate?: number;
  spo2?: number;
  temperature?: number;
  status?: string;
  fused_decision?: {
    final_risk_level: string;
    confidence_score?: number;
    deterministic_flags?: string[];
  };
  delayed_sync?: boolean;
  timestamp?: string;
}

export function useTelemetrySocket(patientId: string, onTelemetryReceived?: (data: TelemetryIngestedEvent) => void) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<TelemetryIngestedEvent | null>(null);
  const ws = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (API_CONFIG.useMockData || !patientId) return;

    try {
      const wsUrl = `${API_CONFIG.wsUrl}/ws/patients/${patientId}`;
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setIsConnected(true);
      };

      ws.current.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as TelemetryIngestedEvent;
          setLastEvent(parsed);
          onTelemetryReceived?.(parsed);
        } catch (err) {
          console.error('Failed to parse telemetry WebSocket payload:', err);
        }
      };

      ws.current.onclose = () => {
        setIsConnected(false);
        // Retry connection after 5 seconds
        setTimeout(() => connect(), 5000);
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
    }
  }, [patientId, onTelemetryReceived]);

  useEffect(() => {
    connect();
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [connect]);

  return {
    isConnected,
    lastEvent,
    reconnect: connect
  };
}
