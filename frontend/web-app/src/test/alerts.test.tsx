import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PropsWithChildren } from 'react';
import { alertsApi, toAlert, vitalsApi } from '@/lib/api';
import { API_CONFIG, API_ENDPOINTS } from '@/lib/config';
import { visibleAlerts } from '@/lib/alerts';
import { useVitals } from '@/hooks/useVitals';

const socket = vi.hoisted(() => ({ onMessage: (_event: unknown) => {} }));
vi.mock('@/hooks/useWebSocket', () => ({
  useVitalsWebSocket: (_id: string, callback: typeof socket.onMessage) => {
    socket.onMessage = callback;
    return { isConnected: true };
  },
}));

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

const raw = { id: 'A1', severity: 'critical', vital_type: 'spo2', message: 'Low oxygen',
  timestamp: '2026-10-25T20:00:00Z', acknowledged: false, dismissed: false };
const alert = toAlert(raw);

describe('alert API boundary', () => {
  it.each(['acknowledge', 'dismiss'] as const)('%s uses POST and returns the action response', async action => {
    const response = action === 'acknowledge'
      ? { alert_id: 'A1', acknowledged: true, acknowledged_at: raw.timestamp, message: 'Alert acknowledged' }
      : { alert_id: 'A1', dismissed: true, dismissed_at: raw.timestamp, message: 'Alert dismissed' };
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => response });
    vi.stubGlobal('fetch', fetch);
    expect(await alertsApi[action]('A1')).toEqual(response);
    const endpoint = action === 'acknowledge' ? API_ENDPOINTS.acknowledgeAlert('A1') : API_ENDPOINTS.dismissAlert('A1');
    expect(fetch).toHaveBeenCalledWith(API_CONFIG.baseUrl + endpoint,
      expect.objectContaining({ method: 'POST', body: '{}' }));
  });

  it('maps dismissed state and timestamps, filters at the hook boundary, and retains acknowledged alerts', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [
      { ...raw, dismissed: true }, { ...raw, id: 'A2', acknowledged: true },
    ] }));
    const mapped = await alertsApi.getAll('P001');
    expect(mapped[0].dismissed).toBe(true);
    expect(mapped[0].timestamp).toBeInstanceOf(Date);
    expect(mapped[0].message).toBe('Low oxygen');
    expect(visibleAlerts(mapped, new Map()).map(a => [a.id, a.acknowledged])).toEqual([['A2', true]]);
  });
});

function mount(useMockData = false) {
  vi.spyOn(vitalsApi, 'getHistory').mockResolvedValue([]);
  vi.spyOn(alertsApi, 'getAll').mockResolvedValue([alert]);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  const wrapper = ({ children }: PropsWithChildren) => <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  return { client, ...renderHook(() => useVitals({ patientId: 'P001', useMockData }), { wrapper }) };
}

describe('confirmed alert actions', () => {
  it.each(['acknowledge', 'dismiss'] as const)('retains the alert when %s fails', async action => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(alertsApi, action).mockRejectedValue(new Error('backend failed'));
    const { result } = mount();
    await waitFor(() => expect(result.current.alerts).toEqual([alert]));
    await act(async () => {
      expect(await (action === 'dismiss' ? result.current.dismissAlert('A1') : result.current.acknowledgeAlert('A1'))).toBe(false);
    });
    expect(result.current.alerts).toEqual([alert]);
  });

  it('does not remove before success, and survives duplicate WebSocket events and stale refetch', async () => {
    let resolve!: (value: Awaited<ReturnType<typeof alertsApi.dismiss>>) => void;
    vi.spyOn(alertsApi, 'dismiss').mockReturnValue(new Promise(done => { resolve = done; }));
    const { result, client } = mount();
    await waitFor(() => expect(result.current.alerts).toHaveLength(1));
    let pending!: Promise<boolean>;
    act(() => { pending = result.current.dismissAlert('A1'); });
    expect(result.current.alerts).toEqual([alert]);
    await act(async () => {
      resolve({ alert_id: 'A1', dismissed: true, dismissed_at: raw.timestamp, message: 'done' });
      expect(await pending).toBe(true);
    });
    act(() => {
      socket.onMessage({ event_type: 'alert.dismissed', payload: { alert_id: 'A1', dismissed: true } });
      socket.onMessage({ event_type: 'alert.dismissed', payload: { alert_id: 'A1', dismissed: true } });
      client.setQueryData(['alerts', 'P001'], [{ ...alert, message: 'stale poll' }, alert]);
    });
    await waitFor(() => expect(result.current.alerts).toEqual([]));
  });

  it('keeps acknowledged alerts visible without duplicates after a stale poll', async () => {
    vi.spyOn(alertsApi, 'acknowledge').mockResolvedValue({ alert_id: 'A1', acknowledged: true, acknowledged_at: raw.timestamp, message: 'done' });
    const { result, client } = mount();
    await waitFor(() => expect(result.current.alerts).toHaveLength(1));
    await act(async () => { expect(await result.current.acknowledgeAlert('A1')).toBe(true); });
    act(() => {
      socket.onMessage({ event_type: 'alert.acknowledged', payload: { alert_id: 'A1', acknowledged: true } });
      client.setQueryData(['alerts', 'P001'], [alert, alert]);
    });
    await waitFor(() => expect(result.current.alerts).toEqual([{ ...alert, acknowledged: true }]));
  });

  it('mock mode returns true without calling the backend', async () => {
    const acknowledge = vi.spyOn(alertsApi, 'acknowledge');
    const dismiss = vi.spyOn(alertsApi, 'dismiss');
    const { result } = mount(true);
    await act(async () => {
      expect(await result.current.acknowledgeAlert('mock')).toBe(true);
      expect(await result.current.dismissAlert('mock')).toBe(true);
    });
    expect(acknowledge).not.toHaveBeenCalled();
    expect(dismiss).not.toHaveBeenCalled();
  });
});
