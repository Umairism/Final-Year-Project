import { useQuery } from '@tanstack/react-query';
import { patientApi } from '@/lib/api';
import { PatientProfile } from '@/types/vitals';

// Mock patient for development (when backend is not available)
const MOCK_PATIENT: PatientProfile = {
  id: '1',
  name: 'Umair Hakeem',
  age: 24,
  gender: 'Male',
  bloodType: 'O+',
  conditions: [],
  medications: [],
  emergencyContacts: [
    {
      name: 'Dr. Ahmed Khan',
      phone: '+92 300 1234567',
      relation: 'Primary Care Physician',
      type: 'doctor',
    },
    {
      name: 'Awais',
      phone: '03145647685',
      relation: 'Brother',
      type: 'family',
    },
  ],
};

export const usePatient = (patientId: string, useMockData: boolean = false) => {
  return useQuery<PatientProfile>({
    queryKey: ['patient', patientId],
    queryFn: async () => {
      if (useMockData) {
        // Return mock data in development
        return MOCK_PATIENT;
      }
      return patientApi.getProfile(patientId);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  });
};
