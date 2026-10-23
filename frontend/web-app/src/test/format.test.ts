import { describe, expect, it } from 'vitest';
import { formatAgeSeconds, formatFixed, formatInt } from '@/lib/format';
describe('format helpers', () => {
  it('formats nulls and decimals', () => { expect(formatInt(null)).toBe('—'); expect(formatInt(116.6)).toBe('117'); expect(formatFixed(36.84, 1)).toBe('36.8'); expect(formatFixed(undefined, 1)).toBe('—'); });
  it('formats ages', () => { expect(formatAgeSeconds(null)).toBe('never'); expect(formatAgeSeconds(12)).toBe('12s ago'); expect(formatAgeSeconds(185)).toBe('3m ago'); expect(formatAgeSeconds(7500)).toBe('2h 5m ago'); });
});
