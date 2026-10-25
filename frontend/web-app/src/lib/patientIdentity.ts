export const resolvePatientId = (user: { patientId?: string | null } | null | undefined) => user?.patientId ?? null;
