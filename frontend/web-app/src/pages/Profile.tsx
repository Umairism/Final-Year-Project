import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { patientApi } from '@/lib/api';
import { buildProfilePayload, profileForm } from '@/lib/profile';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ArrowLeft, User, Heart, Pill, Phone, Save, LogOut } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const Profile = () => {
  const { user, updateProfile, logout } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const patientId = import.meta.env.VITE_PATIENT_ID || 'P001';
  const queryClient = useQueryClient();
  const { data: profile, isLoading, isError, refetch } = useQuery({
    queryKey: ['patient', patientId],
    queryFn: () => patientApi.getProfile(patientId),
    retry: 1,
  });

  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  
  const [formData, setFormData] = useState(() => profileForm());
  useEffect(() => {
    if (profile && !isEditing) setFormData(profileForm(profile));
  }, [profile, isEditing]);

  const handleSave = async () => {
    if (!profile) return;
    setIsSaving(true);
    try {
      const payload = buildProfilePayload(formData, profile);
      const saved = await patientApi.updateProfile(patientId, payload);
      // The server is authoritative. Never mutate caches before PUT succeeds.
      queryClient.setQueryData(['patient', patientId], saved);
      await queryClient.invalidateQueries({ queryKey: ['patient', patientId] });
      const cacheResult = await updateProfile({
        name: saved.name, age: saved.age, gender: saved.gender, bloodType: saved.bloodType,
        medicalConditions: saved.conditions, currentMedications: saved.medications,
        diabetes: saved.diabetes, smokingStatus: saved.smokingStatus,
        emergencyContacts: saved.emergencyContacts,
      });
      setFormData(profileForm(saved));
      setIsEditing(false);
      toast({
        title: 'Profile Updated',
        description: cacheResult.success ? 'Profile saved to the backend.' : 'Profile saved to the backend; local display cache could not be updated.',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to save profile to the backend.',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (!user) return null;
  if (isLoading) return <p className="p-6">Loading patient profile…</p>;
  if (isError || !profile) return (
    <Alert variant="destructive" className="m-6">
      <AlertDescription>Unable to load the backend patient profile. No local or mock profile is being shown.</AlertDescription>
      <Button onClick={() => refetch()}>Retry</Button>
    </Alert>
  );

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto p-6 max-w-4xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <Button variant="ghost" onClick={() => navigate('/dashboard')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Button>
          <Button variant="destructive" onClick={handleLogout}>
            <LogOut className="mr-2 h-4 w-4" />
            Logout
          </Button>
        </div>

        {/* Profile Card */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-2xl">Profile Settings</CardTitle>
                <CardDescription>Demo profile for configured patient {patientId}. Future authentication will bind patients server-side.</CardDescription>
              </div>
              {!isEditing ? (
                <Button onClick={() => setIsEditing(true)}>Edit Profile</Button>
              ) : (
                <div className="flex gap-2">
                  <Button variant="outline" disabled={isSaving} onClick={() => {
                    setIsEditing(false);
                    setFormData(profileForm(profile));
                  }}>
                    Cancel
                  </Button>
                  <Button onClick={handleSave} disabled={isSaving}>
                    <Save className="mr-2 h-4 w-4" />
                    {isSaving ? 'Saving...' : 'Save Changes'}
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Personal Information */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <User className="h-5 w-5 text-blue-600" />
                <h3 className="text-lg font-semibold">Personal Information</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="firstName">First Name</Label>
                  <Input
                    id="firstName"
                    value={formData.firstName}
                    onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                    disabled={!isEditing}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName">Last Name</Label>
                  <Input id="lastName" value={formData.lastName} disabled={!isEditing}
                    onChange={e => setFormData({ ...formData, lastName: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    value={profile.email ?? ''}
                    disabled
                    className="bg-gray-100 dark:bg-gray-800"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="age">Age</Label>
                  <Input
                    id="age"
                    type="number"
                    value={formData.age}
                    onChange={(e) => setFormData({ ...formData, age: parseInt(e.target.value) || 0 })}
                    disabled={!isEditing}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="gender">Gender</Label>
                  <Select
                    value={formData.gender}
                    onValueChange={(value) => setFormData({ ...formData, gender: value })}
                    disabled={!isEditing}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select gender" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Male">Male</SelectItem>
                      <SelectItem value="Female">Female</SelectItem>
                      <SelectItem value="Other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="bloodType">Blood Type</Label>
                  <Select
                    value={formData.bloodType}
                    onValueChange={(value) => setFormData({ ...formData, bloodType: value })}
                    disabled={!isEditing}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select blood type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="A+">A+</SelectItem>
                      <SelectItem value="A-">A-</SelectItem>
                      <SelectItem value="B+">B+</SelectItem>
                      <SelectItem value="B-">B-</SelectItem>
                      <SelectItem value="AB+">AB+</SelectItem>
                      <SelectItem value="AB-">AB-</SelectItem>
                      <SelectItem value="O+">O+</SelectItem>
                      <SelectItem value="O-">O-</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            <Separator />

            {/* Medical Information */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Heart className="h-5 w-5 text-red-600" />
                <h3 className="text-lg font-semibold">Medical Information</h3>
              </div>
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">Age, gender, conditions and medications are used de-identified by HealSense AI. Emergency contact details stay in HealSense for app emergency actions and are not sent to AI.</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Diabetes</Label>
                    <Select value={formData.diabetes} disabled={!isEditing}
                      onValueChange={(diabetes: typeof formData.diabetes) => setFormData({ ...formData, diabetes })}>
                      <SelectTrigger aria-label="Diabetes"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="unknown">Unknown</SelectItem>
                        <SelectItem value="true">Yes</SelectItem>
                        <SelectItem value="false">No</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Smoking</Label>
                    <Select value={formData.smokingStatus} disabled={!isEditing}
                      onValueChange={(smokingStatus: typeof formData.smokingStatus) => setFormData({ ...formData, smokingStatus })}>
                      <SelectTrigger aria-label="Smoking"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="unknown">Unknown</SelectItem>
                        <SelectItem value="non_smoker">Non-smoker</SelectItem>
                        <SelectItem value="former_smoker">Former smoker</SelectItem>
                        <SelectItem value="current_smoker">Current smoker</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="conditions">Medical Conditions</Label>
                  <Input
                    id="conditions"
                    placeholder="Hypertension, Diabetes (comma-separated)"
                    value={formData.medicalConditions}
                    onChange={(e) => setFormData({ ...formData, medicalConditions: e.target.value })}
                    disabled={!isEditing}
                  />
                  {!isEditing && profile.conditions.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {profile.conditions.map((condition, index) => (
                        <Badge key={index} variant="secondary">{condition}</Badge>
                      ))}
                    </div>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="medications">Current Medications</Label>
                  <Input
                    id="medications"
                    placeholder="Aspirin, Metformin (comma-separated)"
                    value={formData.currentMedications}
                    onChange={(e) => setFormData({ ...formData, currentMedications: e.target.value })}
                    disabled={!isEditing}
                  />
                  {!isEditing && profile.medications.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {profile.medications.map((medication, index) => (
                        <Badge key={index} variant="outline">
                          <Pill className="h-3 w-3 mr-1" />
                          {medication}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <Separator />

            {/* Emergency Contacts */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Phone className="h-5 w-5 text-green-600" />
                <h3 className="text-lg font-semibold">Emergency Contacts</h3>
              </div>
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-blue-50 dark:bg-blue-950 rounded-lg">
                  <div className="col-span-2">
                    <Label className="text-blue-900 dark:text-blue-100">Doctor</Label>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="doctorName">Name</Label>
                    <Input
                      id="doctorName"
                      placeholder="Dr. John Smith"
                      value={formData.doctorName}
                      onChange={(e) => setFormData({ ...formData, doctorName: e.target.value })}
                      disabled={!isEditing}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="doctorPhone">Phone</Label>
                    <Input
                      id="doctorPhone"
                      placeholder="+1234567890"
                      value={formData.doctorPhone}
                      onChange={(e) => setFormData({ ...formData, doctorPhone: e.target.value })}
                      disabled={!isEditing}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-purple-50 dark:bg-purple-950 rounded-lg">
                  <div className="col-span-3">
                    <Label className="text-purple-900 dark:text-purple-100">Family Contact</Label>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="familyName">Name</Label>
                    <Input
                      id="familyName"
                      placeholder="Jane Doe"
                      value={formData.familyName}
                      onChange={(e) => setFormData({ ...formData, familyName: e.target.value })}
                      disabled={!isEditing}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="familyPhone">Phone</Label>
                    <Input
                      id="familyPhone"
                      placeholder="+1234567890"
                      value={formData.familyPhone}
                      onChange={(e) => setFormData({ ...formData, familyPhone: e.target.value })}
                      disabled={!isEditing}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="familyRelation">Relation</Label>
                    <Input
                      id="familyRelation"
                      placeholder="Spouse, Sibling, etc."
                      value={formData.familyRelation}
                      onChange={(e) => setFormData({ ...formData, familyRelation: e.target.value })}
                      disabled={!isEditing}
                    />
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Profile;
