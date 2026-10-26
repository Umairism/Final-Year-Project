import { VitalReading } from '@/types/vitals';
export const sparklinePoints = (values: Array<number | null | undefined>, width=160, height=40) => { const nums=values.map(v=>v==null?null:Number(v)); const valid=nums.filter((v):v is number=>v!=null&&Number.isFinite(v)); if(!valid.length)return ''; const min=Math.min(...valid),max=Math.max(...valid),range=max-min||1; const denom=Math.max(nums.length-1,1); return nums.map((v,i)=>{const x=(i/denom)*width; const y=v==null?height/2:height-((v-min)/range)*height; return `${x.toFixed(1)},${y.toFixed(1)}`;}).join(' '); };
export const freshness = (reading?: VitalReading, now=Date.now()) => reading ? Math.max(0,Math.floor((now-reading.timestamp.getTime())/1000)) : null;
export const isFreshReading = (age: number|null) => age != null && age <= 300;
export const spo2ColourBand = (spo2?: number|null) => spo2 == null ? 'unknown' : spo2 >= 95 ? 'cyan' : spo2 >= 92 ? 'amber' : 'rose';
