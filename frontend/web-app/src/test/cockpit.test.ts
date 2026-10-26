import { describe, expect, it } from 'vitest';
import { sparklinePoints, isFreshReading, spo2ColourBand, resolveCockpitRisk, cockpitTrendData } from '@/lib/cockpit';
describe('cockpit helpers',()=>{
 it('handles empty and single sparkline input',()=>{expect(sparklinePoints([])).toBe('');expect(sparklinePoints([3])).toBe('0.0,40.0');});
 it('handles constants, nulls, and rising series',()=>{expect(sparklinePoints([2,2,2])).toContain('0.0,40.0');expect(sparklinePoints([null,2,null])).toContain('80.0,40.0');expect(sparklinePoints([1,2,3]).split(' ')).toHaveLength(3);});
 it('uses the 300 second freshness boundary',()=>{expect(isFreshReading(300)).toBe(true);expect(isFreshReading(301)).toBe(false);expect(isFreshReading(null)).toBe(false);});
 it('maps SpO2 bands and null safely',()=>{expect(spo2ColourBand(95)).toBe('cyan');expect(spo2ColourBand(93)).toBe('amber');expect(spo2ColourBand(91)).toBe('rose');expect(spo2ColourBand(null)).toBe('unknown');});
 it('lets fusion override stored risk without inventing absent scores',()=>{const r=resolveCockpitRisk({status:'warning',riskScore:null} as any,{fused_decision:{final_risk_level:'critical',confidence_score:1,deterministic_flags:['SpO2 low']}},false,null);expect(r.level).toBe('critical');expect(r.storedScore).toBeNull();expect(r.flags).toEqual(['SpO2 low']);});
 it('falls back to stored risk while loading or on error',()=>{expect(resolveCockpitRisk({status:'warning'} as any,undefined,true,null).level).toBe('warning');expect(resolveCockpitRisk({status:'warning'} as any,undefined,false,new Error()).level).toBe('warning');});
 it('maps trend rows with latest values',()=>{const rows=cockpitTrendData([{timestamp:new Date('2026-01-01'),heartRate:70,spo2:98} as any]);expect(rows[0]).toMatchObject({heartRate:70,spo2:98});});
});
