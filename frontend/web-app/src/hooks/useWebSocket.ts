import { useEffect, useRef, useState, useCallback } from 'react';
import { API_CONFIG, WS_TOPICS } from '@/lib/config';

interface UseWebSocketOptions<T> {
  topic: string;
  onMessage: (data: T) => void;
  onError?: (error: Event) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  enabled?: boolean;
  reconnectInterval?: number;
}

export function useWebSocket<T>({
  topic,
  onMessage,
  onError,
  onConnect,
  onDisconnect,
  enabled = true,
  reconnectInterval = 5000,
}: UseWebSocketOptions<T>) {
  const ws = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    if (!enabled || API_CONFIG.useMockData) return;

    try {
      const websocketUrl = `${API_CONFIG.wsUrl}/${topic}`;
      ws.current = new WebSocket(websocketUrl);

      ws.current.onopen = () => {
        console.log(`WebSocket connected to ${topic}`);
        setIsConnected(true);
        onConnect?.();
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as T;
          onMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        onError?.(error);
      };

      ws.current.onclose = () => {
        console.log(`WebSocket disconnected from ${topic}`);
        setIsConnected(false);
        onDisconnect?.();

        // Attempt to reconnect
        if (enabled) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting to reconnect...');
            connect();
          }, reconnectInterval);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
    }
  }, [topic, enabled, onMessage, onError, onConnect, onDisconnect, reconnectInterval]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
  }, []);

  const send = useCallback((data: unknown) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    send,
    disconnect,
    reconnect: connect,
  };
}

// Specific hooks for different data types
export function useVitalsWebSocket(patientId: string, onVitalUpdate: (vital: any) => void) {
  return useWebSocket({
    topic: WS_TOPICS.vitals(patientId),
    onMessage: onVitalUpdate,
    enabled: !API_CONFIG.useMockData,
  });
}

export function useAlertsWebSocket(patientId: string, onAlertUpdate: (alert: any) => void) {
  return useWebSocket({
    topic: WS_TOPICS.alerts(patientId),
    onMessage: onAlertUpdate,
    enabled: !API_CONFIG.useMockData,
  });
}

export function useDeviceWebSocket(deviceId: string, onDeviceUpdate: (status: any) => void) {
  return useWebSocket({
    topic: WS_TOPICS.device(deviceId),
    onMessage: onDeviceUpdate,
    enabled: !API_CONFIG.useMockData,
  });
}
