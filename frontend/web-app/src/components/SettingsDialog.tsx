import { useState } from 'react';
import { VitalThresholds, DEFAULT_THRESHOLDS } from '@/types/vitals';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Label } from '@/components/ui/label';
import { Bell, Sliders, Smartphone, Save } from 'lucide-react';

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const SettingsDialog = ({ open, onOpenChange }: SettingsDialogProps) => {
  const [notifications, setNotifications] = useState({
    pushEnabled: true,
    soundEnabled: true,
    emailEnabled: false,
    criticalOnly: false,
  });

  const [thresholds, setThresholds] = useState(DEFAULT_THRESHOLDS);

  const handleSave = () => {
    // In production, save to backend
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-primary" />
            Settings
          </DialogTitle>
          <DialogDescription>
            Customize your alert thresholds and notification preferences.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="alerts" className="mt-4">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="alerts" className="flex items-center gap-2">
              <Bell className="w-4 h-4" />
              Alerts
            </TabsTrigger>
            <TabsTrigger value="thresholds" className="flex items-center gap-2">
              <Sliders className="w-4 h-4" />
              Thresholds
            </TabsTrigger>
          </TabsList>

          <TabsContent value="alerts" className="space-y-4 mt-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Push Notifications</Label>
                <p className="text-sm text-muted-foreground">
                  Receive alerts on your device
                </p>
              </div>
              <Switch
                checked={notifications.pushEnabled}
                onCheckedChange={(checked) =>
                  setNotifications({ ...notifications, pushEnabled: checked })
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Sound Alerts</Label>
                <p className="text-sm text-muted-foreground">
                  Play sound for critical alerts
                </p>
              </div>
              <Switch
                checked={notifications.soundEnabled}
                onCheckedChange={(checked) =>
                  setNotifications({ ...notifications, soundEnabled: checked })
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Email Notifications</Label>
                <p className="text-sm text-muted-foreground">
                  Send daily summary to email
                </p>
              </div>
              <Switch
                checked={notifications.emailEnabled}
                onCheckedChange={(checked) =>
                  setNotifications({ ...notifications, emailEnabled: checked })
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Critical Alerts Only</Label>
                <p className="text-sm text-muted-foreground">
                  Only notify for critical thresholds
                </p>
              </div>
              <Switch
                checked={notifications.criticalOnly}
                onCheckedChange={(checked) =>
                  setNotifications({ ...notifications, criticalOnly: checked })
                }
              />
            </div>
          </TabsContent>

          <TabsContent value="thresholds" className="space-y-6 mt-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Heart Rate Warning (bpm)</Label>
                <span className="text-sm text-muted-foreground">
                  {thresholds.heartRate.warningMin} - {thresholds.heartRate.warningMax}
                </span>
              </div>
              <Slider
                value={[thresholds.heartRate.warningMin, thresholds.heartRate.warningMax]}
                min={40}
                max={140}
                step={5}
                onValueChange={([min, max]) =>
                  setThresholds({
                    ...thresholds,
                    heartRate: { ...thresholds.heartRate, warningMin: min, warningMax: max },
                  })
                }
              />
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>SpO₂ Warning (%)</Label>
                <span className="text-sm text-muted-foreground">
                  Below {thresholds.spo2.warningMin}%
                </span>
              </div>
              <Slider
                value={[thresholds.spo2.warningMin]}
                min={85}
                max={100}
                step={1}
                onValueChange={([min]) =>
                  setThresholds({
                    ...thresholds,
                    spo2: { ...thresholds.spo2, warningMin: min },
                  })
                }
              />
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Systolic BP Warning (mmHg)</Label>
                <span className="text-sm text-muted-foreground">
                  {thresholds.systolic.warningMin} - {thresholds.systolic.warningMax}
                </span>
              </div>
              <Slider
                value={[thresholds.systolic.warningMin, thresholds.systolic.warningMax]}
                min={80}
                max={180}
                step={5}
                onValueChange={([min, max]) =>
                  setThresholds({
                    ...thresholds,
                    systolic: { ...thresholds.systolic, warningMin: min, warningMax: max },
                  })
                }
              />
            </div>
          </TabsContent>
        </Tabs>

        <div className="flex justify-end mt-4">
          <Button onClick={handleSave} className="gap-2">
            <Save className="w-4 h-4" />
            Save Changes
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
