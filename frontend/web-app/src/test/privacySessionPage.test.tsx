import {beforeEach,describe,expect,it,vi} from 'vitest';
import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import PrivacySession from '@/pages/PrivacySession';

const {useAuth}=vi.hoisted(()=>({useAuth:vi.fn()}));
vi.mock('@/contexts/AuthContext',()=>({useAuth}));

beforeEach(()=>{sessionStorage.clear();useAuth.mockReturnValue({isAuthenticated:false,isLoading:false});vi.stubGlobal('fetch',vi.fn());});

describe('PrivacySession',()=>{
  it('shows reachable state without displaying a credential value',async()=>{vi.mocked(fetch).mockResolvedValue(new Response('{}',{status:200}));render(<MemoryRouter><PrivacySession/></MemoryRouter>);await waitFor(()=>expect(screen.getByText('REACHABLE')).toBeInTheDocument());expect(screen.queryByText(/bearer|jwt/i)).not.toBeInTheDocument();});
  it('shows an honest warning when health is unreachable and still enables Continue',async()=>{vi.mocked(fetch).mockRejectedValue(new Error('offline'));render(<MemoryRouter><PrivacySession/></MemoryRouter>);await waitFor(()=>expect(screen.getByText(/backend health check is currently unreachable/i)).toBeInTheDocument());const button=screen.getByRole('button',{name:/enter landing/i});expect(button).toBeEnabled();fireEvent.click(button);expect(sessionStorage.getItem('healsense_privacy_seen')).toBe('1');});
});
