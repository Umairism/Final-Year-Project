import { EmergencyContact, PatientProfile } from '@/types/vitals';

export interface PatientProfileDto {
  id: string;
  first_name: string;
  last_name: string;
  age: number;
  gender: string;
  blood_type: string | null;
  email?: string | null;
  diabetes: PatientProfile['diabetes'];
  smoking_status: PatientProfile['smokingStatus'];
  medications: string[];
  past_conditions: string[];
  emergency_contacts: EmergencyContact[];
}

export type PatientUpdateDto = Partial<Omit<PatientProfileDto, 'id' | 'email'>>;

export const toPatientProfile = (dto: PatientProfileDto): PatientProfile => ({
  id: dto.id, firstName: dto.first_name, lastName: dto.last_name,
  name: `${dto.first_name} ${dto.last_name}`.trim(), email: dto.email,
  age: dto.age, gender: dto.gender, bloodType: dto.blood_type ?? '',
  diabetes: dto.diabetes, smokingStatus: dto.smoking_status,
  medications: dto.medications, conditions: dto.past_conditions,
  emergencyContacts: dto.emergency_contacts,
});

export const profileForm = (profile?: PatientProfile) => {
  const doctor = profile?.emergencyContacts.find(c => c.type === 'doctor');
  const family = profile?.emergencyContacts.find(c => c.type === 'family');
  return {
    firstName: profile?.firstName ?? '', lastName: profile?.lastName ?? '',
    age: profile?.age ?? 0, gender: profile?.gender ?? '', bloodType: profile?.bloodType ?? '',
    diabetes: profile?.diabetes ?? 'unknown', smokingStatus: profile?.smokingStatus ?? 'unknown',
    medicalConditions: profile?.conditions.join(', ') ?? '',
    currentMedications: profile?.medications.join(', ') ?? '',
    doctorName: doctor?.name ?? '', doctorPhone: doctor?.phone ?? '',
    familyName: family?.name ?? '', familyPhone: family?.phone ?? '', familyRelation: family?.relation ?? '',
  };
};

export const buildProfilePayload = (form: ReturnType<typeof profileForm>, previous: PatientProfile): PatientUpdateDto => {
  if (!Number.isInteger(form.age) || form.age < 0 || form.age > 150) throw new Error('Age must be between 0 and 150.');
  const items = (value: string) => {
    const list = value.split(',').map(item => item.trim()).filter(Boolean);
    if (list.length > 20 || list.some(item => item.length > 100)) throw new Error('Use at most 20 medical entries, each at most 100 characters.');
    return list;
  };
  const makeContact = (name: string, phone: string, relation: string, type: EmergencyContact['type']): EmergencyContact | null => {
    name = name.trim(); phone = phone.trim(); relation = relation.trim();
    if (!name && !phone) return null;
    if (!name || !phone) throw new Error(`Enter both name and phone for the ${type} contact, or leave both blank.`);
    if (name.length > 100 || phone.length < 3 || phone.length > 32 || !relation || relation.length > 100) {
      throw new Error(`Check the ${type} contact name, phone and relation lengths.`);
    }
    return { name, phone, relation, type };
  };
  const firstDoctor = previous.emergencyContacts.find(c => c.type === 'doctor');
  const firstFamily = previous.emergencyContacts.find(c => c.type === 'family');
  // The two editable blocks must not silently remove other stored contacts.
  const contacts = previous.emergencyContacts.filter(c => c !== firstDoctor && c !== firstFamily);
  const doctor = makeContact(form.doctorName, form.doctorPhone, firstDoctor?.relation || 'Primary Care Physician', 'doctor');
  const family = makeContact(form.familyName, form.familyPhone, form.familyRelation, 'family');
  if (doctor) contacts.push(doctor);
  if (family) contacts.push(family);
  if (contacts.length > 5) throw new Error('A maximum of five emergency contacts can be saved.');
  return {
    first_name: form.firstName.trim(), last_name: form.lastName.trim(), age: form.age,
    gender: form.gender, blood_type: form.bloodType || null,
    diabetes: form.diabetes, smoking_status: form.smokingStatus,
    medications: items(form.currentMedications), past_conditions: items(form.medicalConditions),
    emergency_contacts: contacts,
  };
};
