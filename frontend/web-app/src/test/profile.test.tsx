import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { patientApi } from '@/lib/api';
import { buildProfilePayload, PatientProfileDto, profileForm, toPatientProfile } from '@/lib/profile';
import Profile from '@/pages/Profile';

const cache = vi.hoisted(() => ({ update: vi.fn(), toast: vi.fn() }));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({
  user: { name: 'Unrelated local user' }, updateProfile: cache.update, logout: vi.fn(),
}) }));
vi.mock('@/hooks/use-toast', () => ({ useToast: () => ({ toast: cache.toast }) }));

const dto: PatientProfileDto = {
  id: 'P001', first_name: 'Backend', last_name: 'Patient', age: 40, gender: 'Female',
  blood_type: 'A+', diabetes: 'true', smoking_status: 'former_smoker',
  medications: ['Metformin'], past_conditions: ['Type 2 diabetes'],
  emergency_contacts: [
    { name: 'Doctor', phone: '12345', relation: 'Clinician', type: 'doctor' },
    { name: 'Family', phone: '67890', relation: 'Family', type: 'family' },
    { name: 'Other', phone: '54321', relation: 'Support', type: 'other' },
  ],
};

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); cache.update.mockReset(); cache.toast.mockReset(); });

describe('profile mapping and payload', () => {
  it('maps snake_case GET values without invented contacts', () => {
    const profile = toPatientProfile(dto);
    expect(profile).toMatchObject({ name: 'Backend Patient', firstName: 'Backend', lastName: 'Patient',
      bloodType: 'A+', diabetes: 'true', smokingStatus: 'former_smoker',
      medications: ['Metformin'], conditions: ['Type 2 diabetes'], emergencyContacts: dto.emergency_contacts });
    expect(toPatientProfile({ ...dto, emergency_contacts: [] }).emergencyContacts).toEqual([]);
  });

  it('builds normalized PUT payload and preserves unedited other contacts', () => {
    const profile = toPatientProfile(dto);
    const payload = buildProfilePayload({ ...profileForm(profile), diabetes: 'false', smokingStatus: 'non_smoker',
      currentMedications: ' Amlodipine, , Metformin ', medicalConditions: ' Hypertension, ' }, profile);
    expect(payload).toMatchObject({ first_name: 'Backend', last_name: 'Patient', diabetes: 'false',
      smoking_status: 'non_smoker', medications: ['Amlodipine', 'Metformin'], past_conditions: ['Hypertension'] });
    expect(payload.emergency_contacts?.map(c => c.type).sort()).toEqual(['doctor', 'family', 'other']);
    expect(payload.emergency_contacts).toContainEqual(dto.emergency_contacts[2]);
  });

  it('omits blank contact blocks', () => {
    const profile = toPatientProfile({ ...dto, emergency_contacts: [] });
    expect(buildProfilePayload(profileForm(profile), profile).emergency_contacts).toEqual([]);
  });

  it.each(['doctorName', 'doctorPhone', 'familyName', 'familyPhone'] as const)('rejects a half-filled %s block', field => {
    const profile = toPatientProfile({ ...dto, emergency_contacts: [] });
    expect(() => buildProfilePayload({ ...profileForm(profile), [field]: '12345' }, profile)).toThrow('both name and phone');
  });

  it('GET and PUT use typed mapping at fetch boundary', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => dto });
    vi.stubGlobal('fetch', fetch);
    expect((await patientApi.getProfile('P001')).smokingStatus).toBe('former_smoker');
    expect(fetch.mock.calls[0][0]).toMatch(/\/patients\/P001\/profile$/);
    const payload = { diabetes: 'false' as const, emergency_contacts: [] };
    expect((await patientApi.updateProfile('P001', payload)).firstName).toBe('Backend');
    expect(fetch.mock.calls[1][0]).toMatch(/\/patients\/P001$/);
    expect(fetch.mock.calls[1][1]).toMatchObject({ method: 'PUT', body: JSON.stringify(payload) });
  });
});

function mount() {
  vi.spyOn(patientApi, 'getProfile').mockResolvedValue(toPatientProfile(dto));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  render(<QueryClientProvider client={client}><MemoryRouter><Profile /></MemoryRouter></QueryClientProvider>);
  return client;
}

it('loads backend values and Cancel restores them, not Auth values', async () => {
  mount();
  await screen.findByDisplayValue('Backend');
  fireEvent.click(screen.getByText('Edit Profile'));
  fireEvent.change(screen.getByLabelText('First Name'), { target: { value: 'Draft' } });
  fireEvent.click(screen.getByText('Cancel'));
  expect(screen.getByLabelText('First Name')).toHaveValue('Backend');
  expect(cache.update).not.toHaveBeenCalled();
});

it('failed backend save leaves edit mode and caches unchanged', async () => {
  const save = vi.spyOn(patientApi, 'updateProfile').mockRejectedValue(new Error('Backend unavailable'));
  const client = mount();
  await screen.findByDisplayValue('Backend');
  fireEvent.click(screen.getByText('Edit Profile'));
  fireEvent.change(screen.getByLabelText('First Name'), { target: { value: 'Draft' } });
  fireEvent.click(screen.getByText('Save Changes'));
  await waitFor(() => expect(save).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(cache.toast).toHaveBeenCalledWith(expect.objectContaining({ variant: 'destructive' })));
  expect(screen.getByText('Save Changes')).toBeInTheDocument();
  expect(screen.getByLabelText('First Name')).toHaveValue('Draft');
  expect(client.getQueryData(['patient', 'P001'])).toEqual(toPatientProfile(dto));
  expect(cache.update).not.toHaveBeenCalled();
});

it('updates Auth display cache only after the backend resolves', async () => {
  let resolve!: (value: ReturnType<typeof toPatientProfile>) => void;
  vi.spyOn(patientApi, 'updateProfile').mockReturnValue(new Promise(done => { resolve = done; }));
  cache.update.mockResolvedValue({ success: true });
  mount();
  await screen.findByDisplayValue('Backend');
  fireEvent.click(screen.getByText('Edit Profile'));
  fireEvent.click(screen.getByText('Save Changes'));
  expect(cache.update).not.toHaveBeenCalled();
  resolve(toPatientProfile(dto));
  await waitFor(() => expect(cache.update).toHaveBeenCalledWith(expect.objectContaining({
    name: 'Backend Patient', diabetes: 'true', smokingStatus: 'former_smoker', emergencyContacts: dto.emergency_contacts,
  })));
});
