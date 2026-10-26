import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Activity, LogOut, Menu, Monitor, UserRound, X } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { markPrivacySeen } from '@/lib/privacySession';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';

const navClass = 'rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-white/70 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

export default function AppNavbar() {
  const { isAuthenticated, user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const leavePrivacy = (to: string) => { if (to !== '/privacy-session') markPrivacySeen(); setOpen(false); };
  const signOut = async () => { setOpen(false); await logout(); navigate('/login'); };
  const patientLabel = user?.patientId ?? user?.email ?? 'Authenticated';
  const publicLinks = [['Overview', '/'], ['Privacy Session', '/privacy-session']] as const;
  const authLinks = [['Dashboard', '/dashboard'], ['3D Cockpit', '/cockpit?mode=live'], ['Devices', '/devices'], ['Profile', '/profile']] as const;
  return <header className="glass-nav sticky top-0 z-50">
    <div className="mx-auto flex h-[68px] max-w-7xl items-center gap-3 px-4 sm:px-6 lg:px-8">
      <Link to="/" onClick={() => markPrivacySeen()} className="flex min-w-0 items-center gap-3 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-white/80 bg-white/75 text-slate-900 shadow-sm"><Activity className="h-5 w-5" /></span>
        <span className="truncate text-base font-semibold text-slate-900">HealSense <span className="hidden text-sm font-normal text-slate-500 sm:inline">· Remote patient monitoring</span></span>
      </Link>
      <nav aria-label="Primary navigation" className="ml-auto hidden items-center gap-1 lg:flex">
        {(isAuthenticated ? authLinks : publicLinks).map(([label, to]) => <Link key={to} to={to} onClick={() => leavePrivacy(to)} className={`${navClass} ${location.pathname === to.split('?')[0] ? 'bg-slate-900/5 text-slate-900' : ''}`}>{label}</Link>)}
      </nav>
      <div className="ml-2 hidden items-center gap-2 lg:flex">
        {isAuthenticated ? <><span className="glass-chip max-w-[180px] truncate rounded-full px-3 py-2 text-xs font-medium text-slate-600" title={patientLabel}>{patientLabel}</span><Button variant="outline" size="sm" onClick={signOut} className="border-slate-300 bg-white/65 text-slate-700 hover:bg-white"><LogOut className="h-4 w-4" />Sign Out</Button></> : <><Link to="/login" onClick={() => leavePrivacy('/login')} className={navClass}>Sign In</Link><Button asChild size="sm" className="bg-slate-900 text-white hover:bg-slate-700"><Link to="/signup" onClick={() => leavePrivacy('/signup')}>Create Account</Link></Button></>}
      </div>
      <Button variant="outline" size="icon" aria-label="Open navigation menu" className="ml-auto border-slate-300 bg-white/65 text-slate-700 lg:hidden" onClick={() => setOpen(true)}><Menu className="h-5 w-5" /></Button>
    </div>
    <Sheet open={open} onOpenChange={setOpen}><SheetContent side="right" className="glass-panel-strong w-[min(86vw,360px)] border-l border-white/70 p-6"><SheetHeader><SheetTitle className="flex items-center gap-2 text-left text-slate-900"><span className="grid h-8 w-8 place-items-center rounded-lg bg-white text-slate-900 shadow-sm"><Activity className="h-4 w-4" /></span>HealSense</SheetTitle></SheetHeader><nav aria-label="Mobile navigation" className="mt-8 flex flex-col gap-2">{(isAuthenticated ? authLinks : publicLinks).map(([label, to]) => <Link key={to} to={to} onClick={() => leavePrivacy(to)} className={`${navClass} flex items-center gap-3`}><Monitor className="h-4 w-4 text-slate-500" />{label}</Link>)}{isAuthenticated && <><div className="glass-chip mt-4 rounded-lg px-3 py-2 text-sm text-slate-600"><UserRound className="mr-2 inline h-4 w-4" />{patientLabel}</div><Button variant="outline" className="mt-2 justify-start border-slate-300 bg-white/70 text-slate-700" onClick={signOut}><LogOut className="h-4 w-4" />Sign Out</Button></>}{!isAuthenticated && <Button asChild className="mt-3 justify-center bg-slate-900 text-white hover:bg-slate-700"><Link to="/signup" onClick={() => leavePrivacy('/signup')}>Create Account</Link></Button>}</nav></SheetContent></Sheet>
  </header>;
}
