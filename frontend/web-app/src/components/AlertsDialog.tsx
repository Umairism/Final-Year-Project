import { Alert } from '@/types/vitals';
import { format } from 'date-fns';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Bell, CheckCircle, X, AlertTriangle, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AlertsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
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

export const AlertsDialog = ({
  open,
  onOpenChange,
  alerts,
  onAcknowledge,
  onDismiss,
}: AlertsDialogProps) => {
  const unacknowledged = alerts.filter((a) => !a.acknowledged);
  const acknowledged = alerts.filter((a) => a.acknowledged);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-primary" />
            Alerts
            {unacknowledged.length > 0 && (
              <Badge variant="destructive" className="ml-2">
                {unacknowledged.length} new
              </Badge>
            )}
          </DialogTitle>
        </DialogHeader>

        <ScrollArea className="h-[400px] pr-4">
          {alerts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <CheckCircle className="w-12 h-12 text-success mb-4" />
              <p className="font-medium">All Clear!</p>
              <p className="text-sm text-muted-foreground">
                No active alerts at this time
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {unacknowledged.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-muted-foreground">
                    New Alerts
                  </h4>
                  {unacknowledged.map((alert) => (
                    <AlertItem
                      key={alert.id}
                      alert={alert}
                      onAcknowledge={onAcknowledge}
                      onDismiss={onDismiss}
                    />
                  ))}
                </div>
              )}

              {acknowledged.length > 0 && (
                <div className="space-y-2 mt-4">
                  <h4 className="text-sm font-medium text-muted-foreground">
                    Acknowledged
                  </h4>
                  {acknowledged.slice(0, 10).map((alert) => (
                    <AlertItem
                      key={alert.id}
                      alert={alert}
                      onAcknowledge={onAcknowledge}
                      onDismiss={onDismiss}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
};

const AlertItem = ({
  alert,
  onAcknowledge,
  onDismiss,
}: {
  alert: Alert;
  onAcknowledge: (id: string) => void;
  onDismiss: (id: string) => void;
}) => {
  const isCritical = alert.type === 'critical';

  return (
    <div
      className={cn(
        'flex items-start justify-between p-3 rounded-lg border',
        alert.acknowledged
          ? 'bg-muted/50 border-border opacity-60'
          : isCritical
          ? 'bg-destructive/5 border-destructive/20'
          : 'bg-warning/5 border-warning/20'
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'p-1.5 rounded-full',
            isCritical ? 'bg-destructive/10' : 'bg-warning/10'
          )}
        >
          {isCritical ? (
            <AlertCircle className="w-4 h-4 text-destructive" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-warning" />
          )}
        </div>
        <div>
          <p className="text-sm font-medium">
            {vitalLabels[alert.vitalType]}: {alert.value}
          </p>
          <p className="text-xs text-muted-foreground">
            {format(alert.timestamp, 'MMM dd, HH:mm:ss')}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-1">
        {!alert.acknowledged && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onAcknowledge(alert.id)}
            className="h-8 text-xs"
          >
            <CheckCircle className="w-3 h-3 mr-1" />
            Ack
          </Button>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => onDismiss(alert.id)}
        >
          <X className="w-3 h-3" />
        </Button>
      </div>
    </div>
  );
};
