import { useEffect, useRef, useState, useCallback } from 'react';
import { API_CONFIG, WS_TOPICS } from '@/lib/config';

interface UseWebSocketOptions<T> { topic: string; onMessage: (data: T) => void; onError?: (error: Event) => void; onConnect?: () => void; onDisconnect?: () => void; enabled?: boolean; reconnectInterval?: number; }

export function useWebSocket<T>({ topic, onMessage, onError, onConnect, onDisconnect, enabled = true, reconnectInterval = 5000 }: UseWebSocketOptions<T>) {
  const ws = useRef<WebSocket | null>(null); const [isConnected, setIsConnected] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null); const intentional = useRef(false); const mounted = useRef(false); const backoff = useRef(1000);
  const messageRef = useRef(onMessage); const errorRef = useRef(onError); const connectRef = useRef(onConnect); const disconnectRef = useRef(onDisconnect);
  messageRef.current = onMessage; errorRef.current = onError; connectRef.current = onConnect; disconnectRef.current = onDisconnect;

  const connect = useCallback(() => {
    if (!enabled || API_CONFIG.useMockData || !mounted.current) return;
    if (ws.current?.readyState === WebSocket.CONNECTING || ws.current?.readyState === WebSocket.OPEN) return;
    if (timer.current) { clearTimeout(timer.current); timer.current = null; }
    const socket = new WebSocket(`${API_CONFIG.wsUrl}/${topic}`); ws.current = socket;
    socket.onopen = () => { backoff.current = 1000; setIsConnected(true); console.log(`WebSocket connected to ${topic}`); connectRef.current?.(); };
    socket.onmessage = (event) => { try { messageRef.current(JSON.parse(event.data) as T); } catch { console.error(`WebSocket message parse failed for ${topic}`); } };
    socket.onerror = (event) => { console.error(`WebSocket error for ${topic}`); errorRef.current?.(event); };
    socket.onclose = () => { if (ws.current === socket) ws.current = null; if (!intentional.current) { setIsConnected(false); console.log(`WebSocket disconnected from ${topic}`); disconnectRef.current?.(); } if (!intentional.current && enabled && mounted.current) { const delay = Math.max(reconnectInterval, Math.min(backoff.current, 30000)); backoff.current = Math.min(delay * 2, 30000); if (timer.current) clearTimeout(timer.current); timer.current = setTimeout(() => { timer.current = null; connect(); }, delay); } };
  }, [topic, enabled, reconnectInterval]);

  const disconnect = useCallback(() => { intentional.current = true; if (timer.current) { clearTimeout(timer.current); timer.current = null; } if (ws.current) { ws.current.onopen = null; ws.current.onmessage = null; ws.current.onerror = null; ws.current.onclose = null; ws.current.close(); ws.current = null; } setIsConnected(false); }, []);
  const send = useCallback((data: unknown) => { if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(JSON.stringify(data)); }, []);
  useEffect(() => { mounted.current = true; intentional.current = false; connect(); return () => { mounted.current = false; disconnect(); }; }, [connect, disconnect]);
  return { isConnected, send, disconnect, reconnect: connect };
}

export function useVitalsWebSocket(patientId: string, onVitalUpdate: (vital: any) => void, hasPatient = true) { return useWebSocket({ topic: WS_TOPICS.vitals(patientId), onMessage: onVitalUpdate, enabled: !API_CONFIG.useMockData && hasPatient }); }
export function useAlertsWebSocket(patientId: string, onAlertUpdate: (alert: any) => void) { return useWebSocket({ topic: WS_TOPICS.alerts(patientId), onMessage: onAlertUpdate, enabled: !API_CONFIG.useMockData && Boolean(patientId) }); }
export function useDeviceWebSocket(deviceId: string, onDeviceUpdate: (status: any) => void) { return useWebSocket({ topic: WS_TOPICS.device(deviceId), onMessage: onDeviceUpdate, enabled: !API_CONFIG.useMockData }); }
