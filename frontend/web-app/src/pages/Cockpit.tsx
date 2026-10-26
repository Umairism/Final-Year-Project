import {useEffect,useMemo,useState} from 'react';
import {useNavigate,useSearchParams} from 'react-router-dom';
import {useQuery} from '@tanstack/react-query';
import {useAuth} from '@/contexts/AuthContext';
import {usePatient} from '@/hooks/usePatient';
import {useVitals} from '@/hooks/useVitals';
import {useFusionRisk} from '@/hooks/useFusionRisk';
import {useScopedDarkTheme} from '@/hooks/useScopedDarkTheme';
import {API_CONFIG} from '@/lib/config';
import {deviceApi} from '@/lib/api';
import {freshness,resolveCockpitRisk} from '@/lib/cockpit';
import {formatAgeSeconds} from '@/lib/format';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Card,CardContent,CardHeader,CardTitle} from '@/components/ui/card';
import {Sheet,SheetContent,SheetHeader,SheetTitle} from '@/components/ui/sheet';
import {BpEntryDialog} from '@/components/vitals/BpEntryDialog';
import {PatientAssistantPanel} from '@/components/ai/PatientAssistantPanel';
import BodySpecimenCanvas from '@/components/cockpit/specimen/BodySpecimenCanvas';
import OscilloscopeCanvas from '@/components/cockpit/specimen/OscilloscopeCanvas';
import {toCockpitTelemetry} from '@/components/cockpit/specimen/cockpitTelemetry';
import {ScenarioName} from '@/components/cockpit/specimen/specimenTypes';
import {scenarios} from '@/components/cockpit/specimen/simulationScenarios';
import {SharedBeatClock} from '@/components/cockpit/specimen/sharedBeatClock';
import {cockpitSearchParams,parseCockpitQuery} from '@/lib/demoFlow';
import DemoFlowStrip from '@/components/landing/DemoFlowStrip';

const panel='border-white/10 bg-slate-950/70 text-slate-100';

export default function Cockpit(){
  useScopedDarkTheme();
  const {user,logout}=useAuth();const nav=useNavigate();const patientId=user?.patientId??'';
  const {data:patient,isLoading,isError}=usePatient(patientId,false);const vitals=useVitals({patientId,useMockData:API_CONFIG.useMockData});
  const {data:sources}=useQuery({queryKey:['cockpit-sources',patientId],queryFn:()=>deviceApi.getPatientSources(patientId),enabled:Boolean(patientId)&&!API_CONFIG.useMockData,refetchInterval:10000});
  const reading=vitals.currentReading;const fusion=useFusionRisk(patientId,reading,Boolean(patientId));const risk=resolveCockpitRisk(reading,fusion.data,fusion.isLoading,fusion.error);
  const [now,setNow]=useState(Date.now());const [assistant,setAssistant]=useState(false);const [bp,setBp]=useState(false);const [searchParams,setSearchParams]=useSearchParams();const flow=useMemo(()=>parseCockpitQuery(searchParams.toString()),[searchParams]);const sim:ScenarioName=flow.mode==='simulation'?flow.scenario??'stable':'live';const beatClock=useMemo(()=>new SharedBeatClock(),[]);
  useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer)},[]);
  useEffect(()=>{const handle=(event:KeyboardEvent)=>{if((event.metaKey||event.ctrlKey)&&event.key.toLowerCase()==='k'&&sim==='live'){event.preventDefault();setAssistant(value=>!value);}};addEventListener('keydown',handle);return()=>removeEventListener('keydown',handle);},[sim]);
  const age=freshness(reading,now);const telemetry=useMemo(()=>toCockpitTelemetry(reading,age,sim),[reading,age,sim]);
  if(!patientId)return <Loading text="Loading account…"/>;if(isLoading)return <Loading text="Loading patient…"/>;if(isError||!patient)return <div className="min-h-screen bg-[#030611] p-8 text-rose-300">Unable to load patient</div>;
  const source=sources?.dataSources.find(item=>item.deviceId===sources.primarySource)??sources?.dataSources[0];
  const selectFlow=(next:ScenarioName)=>setSearchParams(cockpitSearchParams(next==='live'?{mode:'live'}:{mode:'simulation',scenario:next}),{replace:true});
  return <div className="min-h-screen bg-[#030611] text-slate-100"><DemoFlowStrip compact/>
    <header className="sticky top-0 z-20 border-b border-white/10 bg-slate-950/90 p-4 backdrop-blur"><div className="mx-auto flex max-w-7xl flex-wrap items-center gap-2"><Button variant="outline" className="border-white/10 bg-white/[.04]" onClick={()=>nav('/dashboard')}>← Dashboard</Button><div className="mr-auto"><h1 className="text-xl font-semibold tracking-tight">HealSense Biological Specimen Cockpit</h1><p className="text-xs text-slate-400">{patient.name} · {patient.age} yrs · {patient.gender} · {patient.bloodType}</p></div><Button variant="outline" disabled={sim!=='live'} className="border-cyan-400/30 bg-cyan-500/10 disabled:opacity-60" onClick={()=>setAssistant(true)}>Clinical Assistant <span className="ml-2 text-xs text-slate-400">⌘K</span></Button><Button variant="outline" className="border-white/10 bg-white/[.04]" onClick={async()=>{await logout();nav('/login')}}>Logout</Button></div><div className="mx-auto mt-3 flex max-w-7xl flex-wrap items-center gap-2 text-xs"><Badge className="border-white/10 bg-white/[.04] text-slate-200">{sim==='live'?'LIVE BACKEND':'SIMULATION MODE — presentation values, not patient telemetry'}</Badge><Badge className="border-white/10 bg-white/[.04] text-slate-200">Source: {source?.deviceId??'—'}</Badge>{age!=null&&<Badge className="border-white/10 bg-white/[.04] text-slate-200">Latest: {formatAgeSeconds(age)}</Badge>}<div className="ml-auto flex flex-wrap gap-1">{(['live','stable','tachycardia','hypoxia'] as ScenarioName[]).map(name=><button key={name} onClick={()=>selectFlow(name)} className={`rounded border px-2 py-1 ${sim===name?'border-amber-400/50 bg-amber-500/20 text-amber-200':'border-white/10 text-slate-400'}`}>{name==='live'?'Return to Live':name}</button>)}</div></div></header>
    <main className="mx-auto grid max-w-7xl gap-5 p-5 lg:grid-cols-[.9fr_1.35fr]"><section className="space-y-4"><div className="grid gap-3 sm:grid-cols-2"><VitalCard title="Heart Rate" value={telemetry.heartRate==null?'—':`${telemetry.heartRate.toFixed(0)} bpm`} color="text-rose-300"/><VitalCard title="SpO₂" value={telemetry.spo2==null?'—':`${telemetry.spo2.toFixed(0)}%`} color="text-cyan-300"/><VitalCard title="Temperature" value={telemetry.temperature==null?'—':`${telemetry.temperature.toFixed(1)} °C`} color="text-amber-300"/><VitalCard title="Blood Pressure" value={sim==='live'&&reading?.systolic!=null&&reading?.diastolic!=null?`${reading.systolic}/${reading.diastolic} mmHg`:'—'} color="text-violet-300" onClick={()=>setBp(true)}/></div><Card className={panel}><CardHeader><CardTitle className="text-xs uppercase tracking-[.18em] text-slate-300">Synthetic ECG / PPG-style waveforms</CardTitle></CardHeader><CardContent className="space-y-3"><p className="text-xs text-slate-400">Synthetic ECG/PPG-style waveforms generated from BPM for visualization — HealSense does not measure ECG.</p><div className="h-24 rounded border border-white/10 bg-[#01040a]"><OscilloscopeCanvas bpm={telemetry.bpm} type="ecg" active={telemetry.isFresh||telemetry.simulated} beatClock={beatClock}/></div><div className="h-20 rounded border border-white/10 bg-[#01040a]"><OscilloscopeCanvas bpm={telemetry.bpm} type="ppg" active={telemetry.isFresh||telemetry.simulated} beatClock={beatClock}/></div></CardContent></Card><Card className={panel}><CardHeader><CardTitle className="text-xs uppercase tracking-[.18em]">Fusion confidence</CardTitle></CardHeader><CardContent><div className="flex flex-wrap items-center gap-3"><span className="rounded border border-cyan-400/30 bg-cyan-500/10 px-3 py-2 font-semibold uppercase text-cyan-200">{sim==='live'?risk.level:scenarios[sim].status}</span><span className="text-sm text-slate-300">{sim==='live'&&risk.confidence!=null?`${Math.round(risk.confidence*100)}% confidence`:'Presentation risk'}</span></div>{sim==='live'&&risk.flags.length>0&&<p className="mt-3 text-xs text-rose-300">{risk.flags.join(' · ')}</p>}{sim!=='live'&&<p className="mt-3 text-xs text-amber-200">Assistant uses live backend patient data — return to Live.</p>}</CardContent></Card></section><section className="space-y-4"><BodySpecimenCanvas telemetry={telemetry} beatClock={beatClock}/>{telemetry.respiratoryRate==null&&<p className="text-xs text-amber-300">Respiratory rate unavailable — idle motion illustrative</p>}{sim!=='live'&&<p className="rounded border border-amber-400/30 bg-amber-500/10 p-3 text-xs text-amber-200">SIMULATION MODE — presentation values, not patient telemetry. No backend readings, BP, alerts, or emergency actions are sent.</p>}</section></main>
    <Sheet open={assistant&&sim==='live'} onOpenChange={setAssistant}><SheetContent className="border-white/10 bg-slate-950 text-slate-100"><SheetHeader><SheetTitle>Clinical Assistant</SheetTitle></SheetHeader><PatientAssistantPanel/></SheetContent></Sheet><BpEntryDialog open={bp} onOpenChange={setBp} patientId={patientId}/>
  </div>;
}
function Loading({text}:{text:string}){return <div className="flex min-h-screen items-center justify-center bg-[#030611] text-slate-200">{text}</div>}
function VitalCard({title,value,color,onClick}:{title:string;value:string;color:string;onClick?:()=>void}){return <Card className={panel}><CardHeader className="pb-2"><CardTitle className="text-xs uppercase tracking-[.18em] text-slate-400">{title}</CardTitle></CardHeader><CardContent><button onClick={onClick} className={`w-full text-left text-2xl font-semibold tabular-nums ${color}`}>{value}</button></CardContent></Card>}
