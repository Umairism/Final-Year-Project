import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/badge';
import { Badge } from '@/components/ui/badge';
import { Heart } from 'lucide-react';

interface HeartRateCardProps {
  heartRate: number;
  status?: 'normal' | 'warning' | 'critical';
  delayedSync?: boolean;
}

export const HeartRateCard: React.FC<HeartRateCardProps> = ({
  heartRate,
  status = 'normal',
  delayedSync = false,
}) => {
  const getStatusColor = () => {
    if (status === 'critical') return 'text-destructive border-destructive bg-destructive/10';
    if (status === 'warning') return 'text-amber-500 border-amber-500 bg-amber-500/10';
    return 'text-emerald-500 border-emerald-500 bg-emerald-500/10';
  };

  return (
    <div className="rounded-xl border bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Heart className="h-5 w-5 text-rose-500 animate-pulse" />
          <span className="text-sm font-medium text-muted-foreground">Heart Rate</span>
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
        <span className="text-3xl font-bold">{heartRate}</span>
        <span className="ml-1 text-sm text-muted-foreground">BPM</span>
      </div>
    </div>
  );
};
