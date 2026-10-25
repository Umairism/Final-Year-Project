import { useQuery } from '@tanstack/react-query';
import { aiApi } from '@/lib/api';
import { API_CONFIG } from '@/lib/config';
import { VitalReading } from '@/types/vitals';

export const useFusionRisk = (patientId: string, reading?: VitalReading, enabled = true) => {
  const status = reading?.status ?? 'unknown';
  const bucket = reading?.riskScore == null ? 'none' : Math.round(reading.riskScore / 0.05) * 0.05;
  const bpCrisis = Boolean(reading && reading.systolic != null && reading.diastolic != null && (reading.systolic >= 180 || reading.diastolic >= 120));
  const spo2Low = Boolean(reading && reading.spo2 < 92);
  return useQuery({
    queryKey: ['fusion-risk', patientId, status, bucket, spo2Low, bpCrisis],
    queryFn: () => aiApi.getFusionRisk(patientId),
    enabled: enabled && !API_CONFIG.useMockData && Boolean(patientId) && Boolean(reading), retry: false,
    refetchOnWindowFocus: false, refetchOnReconnect: false, staleTime: 5 * 60 * 1000,
  });
};
