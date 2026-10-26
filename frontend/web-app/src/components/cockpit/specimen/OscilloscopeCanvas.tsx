import {useEffect,useRef} from 'react';
import {CRTOscilloscope} from './oscilloscope';
import {SharedBeatClock} from './sharedBeatClock';

export default function OscilloscopeCanvas({bpm,type,active=true,beatClock}:{bpm:number;type:'ecg'|'ppg';active?:boolean;beatClock:SharedBeatClock}){const ref=useRef<HTMLCanvasElement>(null);const osc=useRef<CRTOscilloscope>();useEffect(()=>{if(!ref.current)return;osc.current=new CRTOscilloscope(ref.current,type==='ecg'?'#fb7185':'#22d3ee',type==='ecg'?'#fb7185':'#22d3ee',type);let raf=0;const tick=()=>{osc.current?.update(bpm,beatClock.phase(bpm),active);raf=requestAnimationFrame(tick);};raf=requestAnimationFrame(tick);const resize=()=>osc.current?.resize();addEventListener('resize',resize);return()=>{cancelAnimationFrame(raf);removeEventListener('resize',resize);};},[type,active,beatClock,bpm]);return <canvas ref={ref} className="h-full w-full" aria-label={`Synthetic ${type.toUpperCase()} style waveform`}/>;}
