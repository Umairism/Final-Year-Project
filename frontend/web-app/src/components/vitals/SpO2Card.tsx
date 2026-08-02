import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Wind } from 'lucide-react';

interface SpO2CardProps {
  spo2: number;
  status?: 'normal' | 'warning' | 'critical';
  delayedSync?: boolean;
}

export const SpO2Card: React.FC<SpO2CardProps> = ({
  spo2,
  status = 'normal',
  delayedSync = false,
}) => {
  const getStatusColor = () => {
    if (status === 'critical' || spo2 < 92) return 'text-destructive border-destructive bg-destructive/10';
    if (status === 'warning' || spo2 < 95) return 'text-amber-500 border-amber-500 bg-amber-500/10';
    return 'text-emerald-500 border-emerald-500 bg-emerald-500/10';
  };

  return (
    <div className="rounded-xl border bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wind className="h-5 w-5 text-sky-500" />
          <span className="text-sm font-medium text-muted-foreground">Blood Oxygen (SpO₂)</span>
        </div>
        <div className="flex gap-2">
          {delayedSync && (
            <Badge variant="outline" className="text-xs bg-muted text-muted-foreground">
              Delayed Sync
            </Badge>
          )}
          <Badge variant="outline" className={`capitalize ${getStatusColor()}`}>
            {status}
          </Badge>
        </div>
      </div>
      <div className="mt-4">
        <span className="text-3xl font-bold">{spo2}</span>
        <span className="ml-1 text-sm text-muted-foreground">%</span>
      </div>
    </div>
  );
};
