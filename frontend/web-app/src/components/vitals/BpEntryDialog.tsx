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
  const [error, setError] = useState(''); const [result, setResult] = useState<{ category: string; alert_id?: string | null }>();
  const history = useQuery({ queryKey: ['bp-history', patientId], queryFn: () => bpApi.history(patientId, 5), enabled: open });
  const mutation = useMutation({ mutationFn: (payload: BpEntryPayload) => bpApi.record(patientId, payload), onSuccess: (data) => {
    setResult(data); queryClient.invalidateQueries({ queryKey: ['vitals-history', patientId] }); queryClient.invalidateQueries({ queryKey: ['alerts', patientId] }); queryClient.invalidateQueries({ queryKey: ['patient-device-sources', patientId] });
  }});
  useEffect(() => { if (open) setTimeout(() => first.current?.focus(), 0); }, [open]);
  const submit = (e: React.FormEvent) => { e.preventDefault(); setError(''); const s=Number(sys), d=Number(dia); if (!sys || !dia || s<60 || s>260 || d<30 || d>200 || s-d<10) { setError(!sys || !dia ? 'Systolic and diastolic are required.' : s-d<10 ? 'Systolic must be at least 10 mmHg higher than diastolic.' : 'Enter values within the allowed ranges.'); return; }
    mutation.mutate({ systolic_bp:s, diastolic_bp:d, ...(pulse ? {pulse:Number(pulse)} : {}), measured_at: measuredAt ? new Date(measuredAt).toISOString() : undefined, note: note || undefined, bp_source:'manual_entry' }); };
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent><DialogHeader><DialogTitle>Log blood pressure</DialogTitle></DialogHeader>
    <form onSubmit={submit} className="space-y-4"><div className="grid grid-cols-2 gap-3"><div><Label htmlFor="systolic">Systolic</Label><Input ref={first} id="systolic" type="number" value={sys} onChange={e=>setSys(e.target.value)} /></div><div><Label htmlFor="diastolic">Diastolic</Label><Input id="diastolic" type="number" value={dia} onChange={e=>setDia(e.target.value)} /></div></div>
    <div><Label htmlFor="pulse">Pulse (optional)</Label><Input id="pulse" type="number" value={pulse} onChange={e=>setPulse(e.target.value)} /></div><div><Label htmlFor="measured-at">Measured at</Label><Input id="measured-at" type="datetime-local" value={measuredAt} onChange={e=>setMeasuredAt(e.target.value)} /></div><div><Label htmlFor="note">Note (optional)</Label><Input id="note" value={note} onChange={e=>setNote(e.target.value)} /></div>
    {error && <p className="text-sm text-destructive">{error}</p>}{mutation.error && <p className="text-sm text-destructive">{(mutation.error as Error).message}</p>}{result && <p className={result.category==='hypertensive_crisis'?'text-sm font-semibold text-destructive':'text-sm text-green-600'}>{result.category}{result.alert_id ? ` — alert ${result.alert_id}` : ''}</p>}
    <Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Saving…' : 'Save BP'}</Button></form>
    <div><h4 className="font-medium">Recent readings</h4>{history.data?.map((r,i)=><p key={i} className="text-sm text-muted-foreground">{r.measured_at ? new Date(r.measured_at).toLocaleString() : '—'} · {r.systolic_bp}/{r.diastolic_bp} · {r.category}</p>)}</div>
  </DialogContent></Dialog>;
}
