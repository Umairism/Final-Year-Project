import { describe, expect, it, beforeEach, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import { authApi, patientApi, getAuthErrorMessage } from '@/lib/api';
import { clearAccessToken, getAccessToken, setAccessToken } from '@/lib/authToken';
import { resolvePatientId } from '@/lib/patientIdentity';
import { API_CONFIG } from '@/lib/config';

vi.mock('@/lib/api', async () => { const actual=await vi.importActual<any>('@/lib/api'); return {...actual, authApi:{register:vi.fn(),login:vi.fn(),verifyEmail:vi.fn(),resendVerification:vi.fn(),me:vi.fn()},patientApi:{getProfile:vi.fn()}}; });
const wrapper=({children}:{children:React.ReactNode})=><AuthProvider>{children}</AuthProvider>;
const basic={id:'u1',email:'u@example.com',full_name:'Test User',patient_id:'P_NEW',is_email_verified:true};
beforeEach(()=>{localStorage.clear();vi.clearAllMocks();(API_CONFIG as any).useMockData=false;});

describe('auth helpers',()=>{
 it('maps safe backend auth errors',()=>{expect(getAuthErrorMessage({status:401,detail:{error:'invalid_credentials'}})).toBe('Invalid email or password.');expect(getAuthErrorMessage({status:422})).toContain('highlighted');expect(getAuthErrorMessage(new Error('network'))).toBe('Cannot reach the HealSense backend.');});
 it('round-trips and clears the access token',()=>{setAccessToken('fake-jwt');expect(getAccessToken()).toBe('fake-jwt');clearAccessToken();expect(getAccessToken()).toBeNull();});
 it('resolves only the authenticated patient id',()=>{expect(resolvePatientId({patientId:'P001'})).toBe('P001');expect(resolvePatientId(null)).toBeNull();expect(resolvePatientId({})).toBeNull();});
});

describe('AuthContext',()=>{
 it('logs in, stores JWT, loads profile, and never stores password',async()=>{vi.mocked(authApi.login).mockResolvedValue({access_token:'fake-jwt',token_type:'bearer',expires_in:10,user:basic});vi.mocked(authApi.me).mockResolvedValue(basic);vi.mocked(patientApi.getProfile).mockResolvedValue({id:'P_NEW',name:'Test User',firstName:'Test',lastName:'User',age:22,gender:'Male',bloodType:'O+',conditions:[],medications:[],emergencyContacts:[]});const {result}=renderHook(()=>useAuth(),{wrapper});await waitFor(()=>expect(result.current.isLoading).toBe(false));await act(async()=>{expect((await result.current.login('u@example.com','Secret123')).success).toBe(true);});expect(getAccessToken()).toBe('fake-jwt');expect(localStorage.getItem('healsense_auth_token')).not.toContain('Secret123');expect(result.current.user?.patientId).toBe('P_NEW');});
 it('signs up without logging in or storing a token',async()=>{vi.mocked(authApi.register).mockResolvedValue({user:{...basic,is_email_verified:false},verification_required:true,email_delivery:{mode:'dev_log',sent:true}});const {result}=renderHook(()=>useAuth(),{wrapper});await waitFor(()=>expect(result.current.isLoading).toBe(false));let response;await act(async()=>{response=await result.current.signup('new@example.com','Secret123','New User',30,'O+','Male');});expect(response).toMatchObject({success:true,verificationRequired:true});expect(getAccessToken()).toBeNull();expect(result.current.user).toBeNull();});
 it('clears legacy JSON tokens and restores 401 sessions logged out',async()=>{localStorage.setItem('healsense_auth_token',JSON.stringify({userId:'old'}));localStorage.setItem('healsense_mock_users','legacy');const {result}=renderHook(()=>useAuth(),{wrapper});await waitFor(()=>expect(result.current.isLoading).toBe(false));expect(getAccessToken()).toBeNull();expect(localStorage.getItem('healsense_mock_users')).toBeNull();});
 it('logout clears token and user',async()=>{setAccessToken('jwt');vi.mocked(authApi.me).mockResolvedValue(basic);const {result}=renderHook(()=>useAuth(),{wrapper});await waitFor(()=>expect(result.current.isLoading).toBe(false));await act(async()=>result.current.logout());expect(result.current.user).toBeNull();expect(getAccessToken()).toBeNull();});
});
