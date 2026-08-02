import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Activity } from 'lucide-react';
import { BpSource } from '@/types/telemetry';

interface BloodPressureCardProps {
  systolic?: number | null;
  diastolic?: number | null;
  bpSource?: BpSource;
  status?: 'normal' | 'warning' | 'critical';
  delayedSync?: boolean;
}

export const BloodPressureCard: React.FC<BloodPressureCardProps> = ({
  systolic,
  diastolic,
  bpSource = 'none',
  status = 'normal',
  delayedSync = false,
}) => {
  const renderSourceBadge = () => {
    switch (bpSource) {
      case 'manual_entry':
        return <Badge variant="secondary" className="bg-blue-500/10 text-blue-500 border-blue-500/20">Source: Manual Entry</Badge>;
      case 'ble_cuff':
        return <Badge variant="secondary" className="bg-purple-500/10 text-purple-500 border-purple-500/20">Source: BLE Cuff</Badge>;
      case 'hardware_uart':
        return <Badge variant="secondary" className="bg-indigo-500/10 text-indigo-500 border-indigo-500/20">Source: Hardware UART</Badge>;
      case 'none':
      default:
        return <Badge variant="outline" className="text-muted-foreground">Source: No BP Recorded</Badge>;
    }
  };

  const hasReading = systolic != null && diastolic != null;

  return (
    <div className="rounded-xl border bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-indigo-500" />
          <span className="text-sm font-medium text-muted-foreground">Blood Pressure</span>
        </div>
        <div className="flex gap-2">
          {delayedSync && (
            <Badge variant="outline" className="text-xs bg-muted text-muted-foreground">
              Delayed Sync
            </Badge>
          )}
          {renderSourceBadge()}
        </div>
      </div>
      <div className="mt-4">
        {hasReading ? (
          <div>
            <span className="text-3xl font-bold">{systolic}/{diastolic}</span>
            <span className="ml-1 text-sm text-muted-foreground">mmHg</span>
          </div>
        ) : (
          <div>
            <span className="text-xl font-semibold text-muted-foreground">Blood Pressure unavailable</span>
          </div>
        )}
      </div>
    </div>
  );
};
