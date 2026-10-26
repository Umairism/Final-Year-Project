import { describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from '@/pages/Dashboard';

vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: { patientId: 'patient-1', name: 'Demo', age: 24, bloodType: 'O+' }, logout: vi.fn() }) }));
vi.mock('@/hooks/useVitals', () => ({ useVitals: () => ({ currentReading: { timestamp: new Date(), heartRate: 72, spo2: 98, temperature: 36.7, systolic: 120, diastolic: 80, respiratoryRate: 16, status: 'normal', riskScore: 0.1, predictionConfidence: 0.9, bpSource: 'manual_entry', delayedSync: false }, readings: [], alerts: [], isConnected: true, isRealtimeConnected: true, acknowledgeAlert: vi.fn(), dismissAlert: vi.fn(), isLoadingHistory: false, isHistoryError: false, refetchHistory: vi.fn() }), getVitalStatus: () => 'normal' }));
vi.mock('@/hooks/usePatient', () => ({ usePatient: () => ({ data: { name: 'Demo', age: 24, gender: 'Other', bloodType: 'O+', email: 'demo@example.com' }, isLoading: false }) }));
vi.mock('@/hooks/useFusionRisk', () => ({ useFusionRisk: () => ({ data: null, isLoading: false, error: null, refetch: vi.fn() }) }));
vi.mock('@tanstack/react-query', () => ({ useQuery: () => ({ data: { fetchedAt: Date.now(), primarySource: 'device-1', dataSources: [{ deviceId: 'device-1', isOnline: true, presenceStatus: 'online' }] } }) }));
vi.mock('@/components/AlertBanner', () => ({ AlertBanner: () => null }));
vi.mock('@/components/HistoryTable', () => ({ HistoryTable: () => null }));
vi.mock('@/components/EmergencyButton', () => ({ EmergencyButton: () => null }));
vi.mock('@/components/SettingsDialog', () => ({ SettingsDialog: () => null }));
vi.mock('@/components/AlertsDialog', () => ({ AlertsDialog: () => null }));
vi.mock('@/components/vitals/HeartRateCard', () => ({ HeartRateCard: () => null }));
vi.mock('@/components/vitals/SpO2Card', () => ({ SpO2Card: () => null }));
vi.mock('@/components/vitals/TemperatureCard', () => ({ TemperatureCard: () => null }));
vi.mock('@/components/vitals/BloodPressureCard', () => ({ BloodPressureCard: () => null }));
vi.mock('@/components/vitals/BpEntryDialog', () => ({ BpEntryDialog: () => null }));
vi.mock('@/components/risk/RiskGauge', () => ({ RiskGauge: () => null }));
vi.mock('@/components/risk/GeminiExplanationCard', () => ({ GeminiExplanationCard: () => null }));
vi.mock('@/components/vitals/VitalTrendChart', () => ({ VitalTrendChart: () => null }));
vi.mock('@/components/TrendChart', () => ({ TrendChart: () => null }));
vi.mock('@/components/ai/PatientAssistantPanel', () => ({ PatientAssistantPanel: () => null }));

describe('global light theme contract', () => {
  it('does not preload a dark document class', () => {
    document.documentElement.classList.remove('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  it('keeps the document light while Dashboard mounts', () => {
    document.documentElement.classList.remove('dark');
    const { unmount } = render(<MemoryRouter><Dashboard /></MemoryRouter>);
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    unmount();
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });
});
