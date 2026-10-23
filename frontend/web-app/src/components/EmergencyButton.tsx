import { useState } from 'react';
import { Phone, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { emergencyApi } from '@/lib/api';

export const EmergencyButton = ({ patientId }: { patientId: string }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [result, setResult] = useState<any>(null); const [error, setError] = useState('');

  const handleEmergencyCall = async () => {
    setIsConfirming(true);
    try { setError(''); setResult(await emergencyApi.trigger({ patientId })); } catch (e) { setError((e as Error).message); } finally {
      setIsConfirming(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className={cn(
          'fixed bottom-6 right-6 z-50',
          'w-16 h-16 rounded-full',
          'bg-destructive text-destructive-foreground',
          'shadow-lg hover:shadow-xl',
          'flex items-center justify-center',
          'transition-all duration-300',
          'hover:scale-110 active:scale-95',
          'animate-pulse-ring'
        )}
        aria-label="Emergency Call"
      >
        <Phone className="w-7 h-7" />
      </button>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <Phone className="w-5 h-5" />
              Emergency Alert
            </DialogTitle>
            <DialogDescription>
              This records an emergency event in HealSense and broadcasts it to connected dashboards. It does not place a phone call or send SMS/email in this FYP build.
            </DialogDescription>
          </DialogHeader>

          <div className="p-4 rounded-lg bg-muted">
            <p className="text-sm font-medium mb-2">External emergency-contact integration: Not configured</p>
            {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
            {result && <p className="mt-2 text-sm font-medium">Emergency event recorded<br/>ID: {result.emergency_id}<br/>{result.message}</p>}
          </div>

          <DialogFooter className="flex-col sm:flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => setIsOpen(false)}
              disabled={isConfirming}
            >
              <X className="w-4 h-4 mr-2" />
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleEmergencyCall}
              disabled={isConfirming}
              className="gap-2"
            >
              {result ? 'Done' : isConfirming ? (
                <>
                  <span className="animate-spin">⏳</span>
                  Recording...
                </>
              ) : (
                <>
                  <Phone className="w-4 h-4" />
                  Record Emergency Alert
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};
