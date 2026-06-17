import { useState } from 'react';
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

  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  
  const [formData, setFormData] = useState({
    name: user?.name || '',
    age: user?.age || 0,
    gender: user?.gender || '',
    bloodType: user?.bloodType || '',
    medicalConditions: user?.medicalConditions?.join(', ') || '',
    currentMedications: user?.currentMedications?.join(', ') || '',
    doctorName: user?.emergencyContacts?.[0]?.name || '',
    doctorPhone: user?.emergencyContacts?.[0]?.phone || '',
    familyName: user?.emergencyContacts?.[1]?.name || '',
    familyPhone: user?.emergencyContacts?.[1]?.phone || '',
    familyRelation: user?.emergencyContacts?.[1]?.relation || '',
  });

  const handleSave = async () => {
    setIsSaving(true);

    const updates = {
      name: formData.name,
      age: formData.age,
      gender: formData.gender,
      bloodType: formData.bloodType,
      medicalConditions: formData.medicalConditions.split(',').map(c => c.trim()).filter(Boolean),
      currentMedications: formData.currentMedications.split(',').map(m => m.trim()).filter(Boolean),
      emergencyContacts: [
        {
          name: formData.doctorName,
          phone: formData.doctorPhone,
          relation: 'Primary Care Physician',
          type: 'doctor' as const,
        },
        {
          name: formData.familyName,
          phone: formData.familyPhone,
          relation: formData.familyRelation,
          type: 'family' as const,
        },
      ],
    };

    const result = await updateProfile(updates);

    if (result.success) {
      toast({
        title: 'Profile Updated',
        description: 'Your profile has been successfully updated.',
      });
      setIsEditing(false);
    } else {
      toast({
        title: 'Error',
        description: result.error || 'Failed to update profile',
        variant: 'destructive',
      });
    }

    setIsSaving(false);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (!user) {
    return null;
  }

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
                <CardDescription>Manage your personal and medical information</CardDescription>
              </div>
              {!isEditing ? (
                <Button onClick={() => setIsEditing(true)}>Edit Profile</Button>
              ) : (
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => {
                    setIsEditing(false);
                    setFormData({
                      name: user?.name || '',
                      age: user?.age || 0,
                      gender: user?.gender || '',
                      bloodType: user?.bloodType || '',
                      medicalConditions: user?.medicalConditions?.join(', ') || '',
                      currentMedications: user?.currentMedications?.join(', ') || '',
                      doctorName: user?.emergencyContacts?.[0]?.name || '',
                      doctorPhone: user?.emergencyContacts?.[0]?.phone || '',
                      familyName: user?.emergencyContacts?.[1]?.name || '',
                      familyPhone: user?.emergencyContacts?.[1]?.phone || '',
                      familyRelation: user?.emergencyContacts?.[1]?.relation || '',
                    });
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
                  <Label htmlFor="name">Full Name</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    disabled={!isEditing}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    value={user.email}
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
                <div className="space-y-2">
                  <Label htmlFor="conditions">Medical Conditions</Label>
                  <Input
                    id="conditions"
                    placeholder="Hypertension, Diabetes (comma-separated)"
                    value={formData.medicalConditions}
                    onChange={(e) => setFormData({ ...formData, medicalConditions: e.target.value })}
                    disabled={!isEditing}
                  />
                  {!isEditing && user.medicalConditions.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {user.medicalConditions.map((condition, index) => (
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
                  {!isEditing && user.currentMedications.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {user.currentMedications.map((medication, index) => (
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
