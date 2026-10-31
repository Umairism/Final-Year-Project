import { describe, it, expect } from 'vitest';
import { mergeVitalReadings, convertRealtimeEventToVital } from '@/lib/vitalsReadings';
import { VitalReading } from '@/types/vitals';

describe('mergeVitalReadings - deduplication and chronological ordering', () => {
  it('deduplicates readings with the same vital ID and retains the latest record', () => {
    const existing: VitalReading[] = [
      {
        id: 'vital-1',
        timestamp: new Date('2026-10-30T10:00:00Z'),
        heartRate: 72,
        spo2: 98,
        temperature: 36.6,
        systolic: null,
        diastolic: null,
        respiratoryRate: null,
        dataOrigin: 'device',
      },
    ];

    const duplicateFromWs: VitalReading = {
      id: 'vital-1',
      timestamp: new Date('2026-10-30T10:00:00Z'),
      heartRate: 72,
      spo2: 98,
      temperature: 36.6,
      systolic: null,
      diastolic: null,
      respiratoryRate: null,
      dataOrigin: 'device',
    };

    const merged = mergeVitalReadings(existing, duplicateFromWs);
    expect(merged).toHaveLength(1);
    expect(merged[0].id).toBe('vital-1');
  });

  it('orders incoming readings chronologically by timestamp even when received out-of-order', () => {
    const existing: VitalReading[] = [
      {
        id: 'vital-2',
        timestamp: new Date('2026-10-30T10:02:00Z'),
        heartRate: 75,
        spo2: 97,
        temperature: 36.8,
        systolic: null,
        diastolic: null,
        respiratoryRate: null,
        dataOrigin: 'device',
      },
    ];

    // Older reading arriving later (e.g. from history refetch or delayed sync)
    const olderReading: VitalReading = {
      id: 'vital-1',
      timestamp: new Date('2026-10-30T10:00:00Z'),
      heartRate: 70,
      spo2: 98,
      temperature: 36.5,
      systolic: null,
      diastolic: null,
      respiratoryRate: null,
      dataOrigin: 'device',
    };

    // Newer reading arriving from live WS
    const newerReading: VitalReading = {
      id: 'vital-3',
      timestamp: new Date('2026-10-30T10:05:00Z'),
      heartRate: 80,
      spo2: 99,
      temperature: 36.7,
      systolic: null,
      diastolic: null,
      respiratoryRate: null,
      dataOrigin: 'device',
    };

    const merged = mergeVitalReadings(existing, [newerReading, olderReading]);
    expect(merged).toHaveLength(3);
    expect(merged[0].id).toBe('vital-1');
    expect(merged[1].id).toBe('vital-2');
    expect(merged[2].id).toBe('vital-3');
  });

  it('preserves dataOrigin provenance faithfully without mislabeling device data as simulated', () => {
    const deviceReading: VitalReading = {
      id: 'vital-real-esp32',
      timestamp: new Date('2026-10-30T12:00:00Z'),
      heartRate: 76,
      spo2: 98,
      temperature: 36.7,
      systolic: null,
      diastolic: null,
      respiratoryRate: null,
      dataOrigin: 'device',
    };

    const simulatedReading: VitalReading = {
      id: 'vital-sim-test',
      timestamp: new Date('2026-10-30T12:01:00Z'),
      heartRate: 85,
      spo2: 95,
      temperature: 37.1,
      systolic: 125,
      diastolic: 82,
      respiratoryRate: 18,
      dataOrigin: 'simulated',
    };

    const merged = mergeVitalReadings([], [deviceReading, simulatedReading]);
    expect(merged[0].dataOrigin).toBe('device');
    expect(merged[1].dataOrigin).toBe('simulated');
  });
});

describe('convertRealtimeEventToVital - canonical WebSocket event parsing', () => {
  it('converts a canonical patient.vitals.created event payload to VitalReading', () => {
    const socketEvent = {
      event_type: 'patient.vitals.created',
      timestamp: '2026-10-30T12:30:00.000Z',
      patient_id: 'P_001',
      payload: {
        device_id: 'ESP32_001',
        vital: {
          id: 'v-abc-123',
          patient_id: 'P_001',
          device_id: 'ESP32_001',
          heart_rate: 74.5,
          spo2: 98.0,
          temperature: 36.8,
          systolic_bp: null,
          diastolic_bp: null,
          respiratory_rate: null,
          bp_source: 'none',
          delayed_sync: false,
          timestamp: '2026-10-30T12:30:00.000Z',
          status: 'normal',
          risk_score: 0.12,
          prediction_confidence: 0.88,
          model_version: 'v1.0.2',
          data_origin: 'device',
        },
        fused_decision: {
          final_risk_level: 'normal',
          confidence_score: 0.12,
        },
      },
    };

    const reading = convertRealtimeEventToVital(socketEvent);
    expect(reading).not.toBeNull();
    expect(reading?.id).toBe('v-abc-123');
    expect(reading?.heartRate).toBe(74.5);
    expect(reading?.spo2).toBe(98);
    expect(reading?.temperature).toBe(36.8);
    expect(reading?.systolic).toBeNull();
    expect(reading?.diastolic).toBeNull();
    expect(reading?.status).toBe('normal');
    expect(reading?.dataOrigin).toBe('device');
  });

  it('returns null for malformed or empty socket payloads', () => {
    expect(convertRealtimeEventToVital(null)).toBeNull();
    expect(convertRealtimeEventToVital({})).toBeNull();
    expect(convertRealtimeEventToVital({ payload: {} })).toBeNull();
  });
});

