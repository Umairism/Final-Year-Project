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
