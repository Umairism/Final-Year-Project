export type CockpitMode='live'|'simulation';
export type SimulationScenario='stable'|'tachycardia'|'hypoxia';
export type DemoFlowMode={mode:CockpitMode;scenario?:SimulationScenario};

const scenarios:SimulationScenario[]=['stable','tachycardia','hypoxia'];
const isScenario=(value:string|null):value is SimulationScenario=>Boolean(value&&scenarios.includes(value as SimulationScenario));

export function parseCockpitQuery(search:string):DemoFlowMode{
  const params=new URLSearchParams(search);const mode=params.get('mode');
  if(mode==='simulation')return {mode,scenario:isScenario(params.get('scenario'))?params.get('scenario')!:'stable'};
  return {mode:'live'};
}

export function cockpitSearchParams(flow:DemoFlowMode){
  return flow.mode==='simulation'?{mode:'simulation',scenario:flow.scenario??'stable'}:{mode:'live'};
}

export function currentDemoStep(pathname:string,search=''){
  if(pathname==='/privacy-session')return 1;
  if(pathname==='/')return 2;
  if(pathname==='/login')return 3;
  if(pathname==='/dashboard')return 4;
  if(pathname==='/cockpit')return parseCockpitQuery(search).mode==='simulation'?6:5;
  return 2;
}
