import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { deviceApi } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Cpu, Wifi, WifiOff, Battery, Clock, ShieldCheck } from 'lucide-react';

export const Devices = () => {
  const PATIENT_ID = '1';

  const { data: sourceData, isLoading } = useQuery({
    queryKey: ['patient-device-sources', PATIENT_ID],
    queryFn: () => deviceApi.getPatientSources(PATIENT_ID),
    refetchInterval: 5000,
  });

  const devicesList = sourceData?.data_sources || [
    {
      device_id: 'ESP32_PATIENT_001',
      device_type: 'iot_hardware',
      phone_model: null,
      connected: true,
      battery_level: 95,
      last_seen: new Date().toISOString(),
    },
    {
      device_id: `PHONE_${PATIENT_ID}`,
      device_type: 'mobile_app',
      phone_model: 'Samsung Galaxy S23',
      connected: false,
      battery_level: 80,
      last_seen: new Date().toISOString(),
    }
  ];

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Connected Devices & Gateways</h1>
          <p className="text-sm text-muted-foreground">
            Monitor registered ESP32 IoT gateways and smartphone sensor telemetry nodes.
          </p>
        </div>
        <Badge variant="outline" className="px-3 py-1 bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
          <ShieldCheck className="h-4 w-4 mr-1 inline" /> Hardware Auth Active
        </Badge>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {devicesList.map((dev) => (
          <Card key={dev.device_id} className="relative overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base font-medium flex items-center gap-2">
                <Cpu className="h-5 w-5 text-indigo-500" />
                {dev.device_id}
              </CardTitle>
              {dev.connected ? (
                <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
                  <Wifi className="h-3.5 w-3.5 mr-1" /> Online
                </Badge>
              ) : (
                <Badge variant="outline" className="bg-slate-500/10 text-slate-500 border-slate-500/20">
                  <WifiOff className="h-3.5 w-3.5 mr-1" /> Offline
                </Badge>
              )}
            </CardHeader>
            <CardContent className="space-y-3 pt-4">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Type:</span>
                <span className="font-medium capitalize">{dev.device_type.replace('_', ' ')}</span>
              </div>
              {dev.phone_model && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Model:</span>
                  <span className="font-medium">{dev.phone_model}</span>
                </div>
              )}
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Battery Level:</span>
                <span className="font-medium flex items-center gap-1">
                  <Battery className="h-4 w-4 text-emerald-500" /> {dev.battery_level ?? 100}%
                </span>
              </div>
              <div className="flex justify-between text-sm pt-2 border-t text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" /> Last Heartbeat:
                </span>
                <span>{dev.last_seen ? new Date(dev.last_seen).toLocaleTimeString() : 'N/A'}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};
