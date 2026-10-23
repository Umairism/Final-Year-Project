import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { deviceApi } from '@/lib/api';
import { formatAgeSeconds } from '@/lib/format';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
export const Devices = () => {
  const patientId=import.meta.env.VITE_PATIENT_ID || 'P001'; const qc=useQueryClient();
  const q=useQuery({queryKey:['patient-device-sources',patientId],queryFn:()=>deviceApi.getPatientSources(patientId),refetchInterval:5000});
  const action=useMutation({mutationFn:({id,connected}:{id:string;connected:boolean})=>connected?deviceApi.disconnect(id):deviceApi.connect(id,patientId),onSuccess:()=>qc.invalidateQueries({queryKey:['patient-device-sources',patientId]})});
  if(q.isLoading) return <div className="p-6">Loading devices...</div>; if(q.isError) return <div className="p-6 text-destructive">Unable to load devices: {(q.error as Error).message}</div>;
  const devices=q.data?.dataSources ?? []; if(!devices.length) return <div className="p-6">No devices registered for {patientId}.</div>;
  const label=(s?:string)=>s==='online'?'Online':s==='stale'?'Stale':s==='never_seen'?'Never seen':s==='disabled'?'Disabled':'Unknown';
  return <div className="container mx-auto p-6 space-y-6"><h1 className="text-2xl font-bold">Connected Devices & Gateways</h1>{action.isError&&<p className="text-destructive">{(action.error as Error).message}</p>}<div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">{devices.map(d=><Card key={d.deviceId}><CardHeader><CardTitle>{d.deviceId}</CardTitle><Badge variant={d.isOnline===true?'default':'secondary'}>{label(d.presenceStatus)}</Badge></CardHeader><CardContent className="space-y-3"><div>Type: {d.deviceType ?? '—'}</div><div>Battery: {d.batteryLevel == null?'—':`${d.batteryLevel}%`}</div><div>Last seen: {d.lastSeen ? `${d.lastSeen.toLocaleString()} (${formatAgeSeconds(d.lastSeenSecondsAgo)})` : 'Never'}</div><Button disabled={action.isPending} onClick={()=>action.mutate({id:d.deviceId,connected:d.connected})}>{action.isPending?'Updating…':d.connected?'Disconnect':'Connect'}</Button></CardContent></Card>)}</div></div>;
};
