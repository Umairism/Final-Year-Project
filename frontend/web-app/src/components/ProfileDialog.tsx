import { PatientProfile } from '@/types/vitals';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  User,
  Phone,
  Heart,
  Pill,
  AlertCircle,
  Calendar,
  Droplets,
} from 'lucide-react';

interface ProfileDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  patient: PatientProfile;
}

export const ProfileDialog = ({
  open,
  onOpenChange,
  patient,
}: ProfileDialogProps) => {
  const initials = patient.name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <User className="w-5 h-5 text-primary" />
            Patient Profile
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Header with avatar */}
          <div className="flex items-center gap-4">
            <Avatar className="w-20 h-20">
              <AvatarImage src={patient.avatar} alt={patient.name} />
              <AvatarFallback className="bg-primary/10 text-primary text-2xl font-display font-bold">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div>
              <h3 className="text-xl font-display font-semibold">{patient.name}</h3>
              <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  {patient.age} years
                </span>
                <span>{patient.gender}</span>
              </div>
              <div className="flex items-center gap-1 mt-2">
                <Droplets className="w-4 h-4 text-destructive" />
                <Badge variant="outline" className="text-destructive border-destructive/30">
                  {patient.bloodType}
                </Badge>
              </div>
            </div>
          </div>

          <Separator />

          {/* Medical conditions */}
          <div>
            <h4 className="flex items-center gap-2 font-medium mb-3">
              <Heart className="w-4 h-4 text-primary" />
              Medical Conditions
            </h4>
            <div className="flex flex-wrap gap-2">
              {patient.conditions.length > 0 ? (
                patient.conditions.map((condition) => (
                  <Badge key={condition} variant="secondary">
                    {condition}
                  </Badge>
                ))
              ) : (
                <span className="text-sm text-muted-foreground">No conditions recorded</span>
              )}
            </div>
          </div>

          {/* Medications */}
          <div>
            <h4 className="flex items-center gap-2 font-medium mb-3">
              <Pill className="w-4 h-4 text-primary" />
              Current Medications
            </h4>
            <div className="flex flex-wrap gap-2">
              {patient.medications.length > 0 ? (
                patient.medications.map((med) => (
                  <Badge key={med} variant="outline">
                    {med}
                  </Badge>
                ))
              ) : (
                <span className="text-sm text-muted-foreground">No medications recorded</span>
              )}
            </div>
          </div>

          <Separator />

          {/* Emergency contact */}
          <div className="p-4 rounded-lg bg-destructive/5 border border-destructive/20">
            <h4 className="flex items-center gap-2 font-medium mb-3 text-destructive">
              <AlertCircle className="w-4 h-4" />
              Emergency Contact
            </h4>
            <div className="space-y-2 text-sm">
              <p className="font-medium">{patient.emergencyContact.name}</p>
              <p className="text-muted-foreground">{patient.emergencyContact.relation}</p>
              <p className="flex items-center gap-2">
                <Phone className="w-4 h-4 text-muted-foreground" />
                {patient.emergencyContact.phone}
              </p>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
