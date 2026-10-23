import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { bpApi, BpEntryPayload } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

export function BpEntryDialog({ patientId, open, onOpenChange }: { patientId: string; open: boolean; onOpenChange: (open: boolean) => void }) {
  const first = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const [sys, setSys] = useState(''); const [dia, setDia] = useState(''); const [pulse, setPulse] = useState('');
  const [measuredAt, setMeasuredAt] = useState(new Date().toISOString().slice(0, 16)); const [note, setNote] = useState('');
  const [error, setError] = useState(''); const [result, setResult] = useState<{ category: string; alert_id?: string | null }>(); const [standalone, setStandalone] = useState<string[]>([]); const [hr,setHr]=useState(''); const [spo2,setSpo2]=useState(''); const [temp,setTemp]=useState('');
  const history = useQuery({ queryKey: ['bp-history', patientId], queryFn: () => bpApi.history(patientId, 5), enabled: open });
  const mutation = useMutation({ mutationFn: (payload: BpEntryPayload) => bpApi.record(patientId, payload), onSuccess: (data) => {
    setResult(data); queryClient.invalidateQueries({ queryKey: ['vitals-history', patientId] }); queryClient.invalidateQueries({ queryKey: ['alerts', patientId] }); queryClient.invalidateQueries({ queryKey: ['patient-device-sources', patientId] });
  }, onError: (e: any) => { const detail=e?.detail; if (e?.status===409 && detail?.error==='no_anchor_reading') { setStandalone(detail.missing_fields || ['heart_rate','spo2','temperature']); setError('No wearable reading exists to attach to. Enter the missing vitals for a standalone reading.'); } else setError(typeof detail==='string'?detail:detail?JSON.stringify(detail):e.message); }});
  useEffect(() => { if (open) setTimeout(() => first.current?.focus(), 0); }, [open]);
  const submit = (e: React.FormEvent) => { e.preventDefault(); setError(''); const s=Number(sys), d=Number(dia); if (!sys || !dia || s<60 || s>260 || d<30 || d>200 || s-d<10) { setError(!sys || !dia ? 'Systolic and diastolic are required.' : s-d<10 ? 'Systolic must be at least 10 mmHg higher than diastolic.' : 'Enter values within the allowed ranges.'); return; }
    if (standalone.length && (!hr || !spo2 || !temp || Number(hr)<0 || Number(hr)>300 || Number(spo2)<0 || Number(spo2)>100 || Number(temp)<30 || Number(temp)>45)) { setError('Enter heart rate (0–300), SpO₂ (0–100), and temperature (30–45).'); return; } mutation.mutate({ systolic_bp:s, diastolic_bp:d, ...(pulse ? {pulse:Number(pulse)} : {}), measured_at: measuredAt ? new Date(measuredAt).toISOString() : undefined, note: note || undefined, bp_source:'manual_entry', ...(standalone.length ? {heart_rate:Number(hr),spo2:Number(spo2),temperature:Number(temp)} : {}) }); };
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent><DialogHeader><DialogTitle>Log blood pressure</DialogTitle></DialogHeader>
    <form onSubmit={submit} className="space-y-4"><div className="grid grid-cols-2 gap-3"><div><Label htmlFor="systolic">Systolic</Label><Input ref={first} id="systolic" type="number" value={sys} onChange={e=>setSys(e.target.value)} /></div><div><Label htmlFor="diastolic">Diastolic</Label><Input id="diastolic" type="number" value={dia} onChange={e=>setDia(e.target.value)} /></div></div>
    <div><Label htmlFor="pulse">Pulse (optional)</Label><Input id="pulse" type="number" value={pulse} onChange={e=>setPulse(e.target.value)} /></div><div><Label htmlFor="measured-at">Measured at</Label><Input id="measured-at" type="datetime-local" value={measuredAt} onChange={e=>setMeasuredAt(e.target.value)} /></div><div><Label htmlFor="note">Note (optional)</Label><Input id="note" value={note} onChange={e=>setNote(e.target.value)} /></div>
    {error && <p className="text-sm text-destructive">{error}</p>}{mutation.error && <p className="text-sm text-destructive">{(mutation.error as Error).message}</p>}{result && <p className={result.category==='hypertensive_crisis'?'text-sm font-semibold text-destructive':'text-sm text-green-600'}>{result.category}{result.alert_id ? ` — alert ${result.alert_id}` : ''}</p>}
    {standalone.length > 0 && <div className="space-y-2"><Label htmlFor="heart-rate">Heart rate</Label><Input id="heart-rate" type="number" value={hr} onChange={e=>setHr(e.target.value)} /><Label htmlFor="spo2">SpO₂</Label><Input id="spo2" type="number" value={spo2} onChange={e=>setSpo2(e.target.value)} /><Label htmlFor="temperature">Temperature</Label><Input id="temperature" type="number" value={temp} onChange={e=>setTemp(e.target.value)} /></div>}
    <Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Saving…' : 'Save BP'}</Button></form>
    <div><h4 className="font-medium">Recent readings</h4>{history.data?.map((r,i)=><p key={i} className="text-sm text-muted-foreground">{r.timestamp ? new Date(r.timestamp).toLocaleString() : '—'} · {r.systolic_bp}/{r.diastolic_bp} · {r.status ?? '—'}</p>)}</div>
  </DialogContent></Dialog>;
}
