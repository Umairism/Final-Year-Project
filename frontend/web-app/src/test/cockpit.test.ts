import { describe, expect, it } from 'vitest';
import { sparklinePoints, isFreshReading, spo2ColourBand } from '@/lib/cockpit';
describe('cockpit helpers',()=>{
 it('handles empty and single sparkline input',()=>{expect(sparklinePoints([])).toBe('');expect(sparklinePoints([3])).toBe('0.0,40.0');});
 it('handles constants, nulls, and rising series',()=>{expect(sparklinePoints([2,2,2])).toContain('0.0,40.0');expect(sparklinePoints([null,2,null])).toContain('80.0,40.0');expect(sparklinePoints([1,2,3]).split(' ')).toHaveLength(3);});
 it('uses the 300 second freshness boundary',()=>{expect(isFreshReading(300)).toBe(true);expect(isFreshReading(301)).toBe(false);expect(isFreshReading(null)).toBe(false);});
 it('maps SpO2 bands and null safely',()=>{expect(spo2ColourBand(95)).toBe('cyan');expect(spo2ColourBand(93)).toBe('amber');expect(spo2ColourBand(91)).toBe('rose');expect(spo2ColourBand(null)).toBe('unknown');});
});
