import { VitalReading } from '@/types/vitals';
import { toVitalReading } from '@/lib/api';

/**
 * Deduplicate vital readings by unique ID (or timestamp if ID is missing)
 * and preserve strictly ascending chronological timestamp order.
 */
export function mergeVitalReadings(
  existing: VitalReading[],
  incoming: VitalReading | VitalReading[],
  maxLimit: number = 60
): VitalReading[] {
  const incomingList = Array.isArray(incoming) ? incoming : [incoming];
  if (incomingList.length === 0) return existing;

  const readingMap = new Map<string, VitalReading>();

  const getKey = (r: VitalReading): string => {
    if (r.id && r.id.trim() !== '') return `id:${r.id}`;
    return `ts:${r.timestamp instanceof Date ? r.timestamp.getTime() : new Date(r.timestamp).getTime()}`;
  };

  for (const r of existing) {
    readingMap.set(getKey(r), r);
  }

  for (const r of incomingList) {
    if (!r) continue;
    readingMap.set(getKey(r), r);
  }

  return Array.from(readingMap.values())
    .sort((a, b) => {
      const aTime = a.timestamp instanceof Date ? a.timestamp.getTime() : new Date(a.timestamp).getTime();
      const bTime = b.timestamp instanceof Date ? b.timestamp.getTime() : new Date(b.timestamp).getTime();
      return aTime - bTime;
    })
    .slice(-maxLimit);
}

/**
 * Parse and convert a canonical realtime WebSocket event into a VitalReading.
 * Accepts { event_type: "patient.vitals.created", payload: { vital: { ... } } }
 * or raw vital payloads.
 */
export function convertRealtimeEventToVital(event: unknown): VitalReading | null {
  if (!event || typeof event !== 'object') return null;
  const evt = event as Record<string, unknown>;
  const payload = (evt.payload ?? evt) as Record<string, unknown>;
  const rawVital = (payload.vital ?? payload) as Record<string, unknown>;

  if (!rawVital || typeof rawVital !== 'object') return null;
  const reading = toVitalReading(rawVital);

  if (
    reading.heartRate === 0 &&
    reading.spo2 === 0 &&
    reading.temperature === 0 &&
    !rawVital.heart_rate &&
    !rawVital.heartRate
  ) {
    return null;
  }

  return reading;
}

