import { Check, Circle } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { currentDemoStep } from '@/lib/demoFlow';
import { markPrivacySeen } from '@/lib/privacySession';

const steps = [
  ['Privacy Session', '/privacy-session'], ['Landing', '/'], ['Sign In', '/login'], ['Telemetry', '/dashboard'],
  ['3D Cockpit', '/cockpit?mode=live'], ['Hypoxia Simulation', '/cockpit?mode=simulation&scenario=hypoxia'], ['Return to Live', '/cockpit?mode=live'],
] as const;

export default function DemoFlowStepper() {
  const location = useLocation();
  const active = currentDemoStep(location.pathname, location.search);
  return <section aria-label="Demo journey" className="mx-auto w-full max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
    <div className="glass-panel rounded-2xl px-4 py-4 sm:px-6">
      <div className="mb-3 flex items-center justify-between gap-3"><h2 className="text-sm font-semibold text-slate-900">Demo journey</h2><span className="text-xs text-slate-500 sm:hidden">Step {active} of 7</span></div>
      <nav className="hidden items-start md:flex" aria-label="Demo journey steps">{steps.map(([label, to], index) => { const number = index + 1; const complete = number < active; const current = number === active; return <div key={`${label}-${to}`} className="flex min-w-0 flex-1 items-start"><div className="flex min-w-0 flex-1 flex-col items-center"><Link to={to} onClick={() => { if (number > 1) markPrivacySeen(); }} aria-current={current ? 'step' : undefined} className="group flex min-w-0 flex-col items-center gap-2 rounded-lg px-1 text-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><span className={`grid h-9 w-9 place-items-center rounded-full border text-sm font-semibold transition ${complete ? 'border-slate-900 bg-slate-900 text-white' : current ? 'border-teal-700 bg-slate-900 text-white ring-4 ring-teal-700/15' : 'border-slate-300 bg-slate-100 text-slate-500 group-hover:border-slate-500'}`}>{complete ? <Check className="h-4 w-4" /> : number}</span><span className={`whitespace-nowrap text-sm ${current ? 'font-semibold text-slate-900' : complete ? 'text-slate-700' : 'text-slate-500'}`}>{label}</span></Link></div>{number < steps.length && <span className={`mt-[18px] h-px flex-1 ${number < active ? 'bg-slate-900' : 'bg-slate-200'}`} aria-hidden="true" />}</div>; })}</nav>
      <div className="md:hidden"><div className="mb-2 flex items-center gap-3"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-slate-900 text-sm font-semibold text-white">{active}</span><span className="text-sm font-medium text-slate-900">{steps[active - 1]?.[0] ?? 'Landing'}</span></div><div className="h-2 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-slate-900 transition-all" style={{ width: `${(active / steps.length) * 100}%` }} /></div><div className="mt-3 flex gap-2 overflow-x-auto pb-1">{steps.map(([label, to], index) => <Link key={`${label}-mobile`} to={to} onClick={() => { if (index > 0) markPrivacySeen(); }} className={`snap-start whitespace-nowrap rounded-full border px-3 py-2 text-sm ${index + 1 === active ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white/60 text-slate-600'}`}>{index + 1}. {label}</Link>)}</div></div>
    </div>
  </section>;
}
