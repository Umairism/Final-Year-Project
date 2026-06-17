import { Alert } from '@/types/vitals';
import { X, AlertTriangle, AlertCircle, Bell } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';
import { Button } from '@/components/ui/button';

interface AlertBannerProps {
  alerts: Alert[];
  onAcknowledge: (id: string) => void;
  onDismiss: (id: string) => void;
}

const vitalLabels: Record<string, string> = {
  heartRate: 'Heart Rate',
  spo2: 'SpO₂',
  temperature: 'Temperature',
  systolic: 'Systolic BP',
  diastolic: 'Diastolic BP',
  respiratoryRate: 'Respiratory Rate',
};

export const AlertBanner = ({ alerts, onAcknowledge, onDismiss }: AlertBannerProps) => {
  const unacknowledgedAlerts = alerts.filter((a) => !a.acknowledged);
  const criticalAlerts = unacknowledgedAlerts.filter((a) => a.type === 'critical');
  const warningAlerts = unacknowledgedAlerts.filter((a) => a.type === 'warning');

  if (unacknowledgedAlerts.length === 0) return null;

  return (
    <div className="space-y-2 animate-slide-up">
      {criticalAlerts.slice(0, 3).map((alert) => (
        <div
          key={alert.id}
          className={cn(
            'flex items-center justify-between p-4 rounded-lg border',
            'bg-destructive/10 border-destructive/30'
          )}
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-destructive/20">
              <AlertCircle className="w-5 h-5 text-destructive" />
            </div>
            <div>
              <p className="font-medium text-destructive">
                Critical: {vitalLabels[alert.vitalType]} at {alert.value}
              </p>
              <p className="text-sm text-muted-foreground">
                {formatDistanceToNow(alert.timestamp, { addSuffix: true })}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onAcknowledge(alert.id)}
              className="text-destructive hover:text-destructive hover:bg-destructive/10"
            >
              Acknowledge
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDismiss(alert.id)}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>
      ))}

      {warningAlerts.slice(0, 2).map((alert) => (
        <div
          key={alert.id}
          className={cn(
            'flex items-center justify-between p-4 rounded-lg border',
            'bg-warning/10 border-warning/30'
          )}
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-warning/20">
              <AlertTriangle className="w-5 h-5 text-warning" />
            </div>
            <div>
              <p className="font-medium text-warning">
                Warning: {vitalLabels[alert.vitalType]} at {alert.value}
              </p>
              <p className="text-sm text-muted-foreground">
                {formatDistanceToNow(alert.timestamp, { addSuffix: true })}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onAcknowledge(alert.id)}
              className="text-warning hover:text-warning hover:bg-warning/10"
            >
              Acknowledge
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDismiss(alert.id)}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>
      ))}

      {unacknowledgedAlerts.length > 5 && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground p-2">
          <Bell className="w-4 h-4" />
          <span>+{unacknowledgedAlerts.length - 5} more alerts</span>
        </div>
      )}
    </div>
  );
};
