import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {MemoryRouter,Route,Routes} from 'react-router-dom';
import PrivacySession from '@/pages/PrivacySession';
import Index from '@/pages/Index';

const {useAuth}=vi.hoisted(()=>({useAuth:vi.fn()}));
vi.mock('@/contexts/AuthContext',()=>({useAuth}));

beforeEach(()=>{sessionStorage.clear();useAuth.mockReturnValue({isAuthenticated:false,isLoading:false});vi.stubGlobal('fetch',vi.fn());});
afterEach(()=>cleanup());

describe('PrivacySession',()=>{
  it('shows reachable state without displaying a credential value',async()=>{vi.mocked(fetch).mockResolvedValue(new Response('{}',{status:200}));render(<MemoryRouter><PrivacySession/></MemoryRouter>);await waitFor(()=>expect(screen.getByText('REACHABLE')).toBeInTheDocument());expect(screen.queryByText(/bearer|jwt/i)).not.toBeInTheDocument();});
  it('shows an honest warning when health is unreachable and still enables Continue',async()=>{vi.mocked(fetch).mockRejectedValue(new Error('offline'));render(<MemoryRouter><PrivacySession/></MemoryRouter>);await waitFor(()=>expect(screen.getByText(/backend health check is currently unreachable/i)).toBeInTheDocument());const button=screen.getAllByRole('button',{name:/continue to landing/i})[0];expect(button).toBeEnabled();fireEvent.click(button);expect(sessionStorage.getItem('healsense_privacy_seen')).toBe('1');});
  it('redirects a fresh root visit to Privacy',async()=>{vi.mocked(fetch).mockResolvedValue(new Response('{}',{status:200}));render(<MemoryRouter initialEntries={['/']}><Routes><Route path="/" element={<Index/>}/><Route path="/privacy-session" element={<PrivacySession/>}/></Routes></MemoryRouter>);await waitFor(()=>expect(screen.getByTestId('privacy-session-page')).toBeInTheDocument());});
  it('continues from Privacy to Landing',async()=>{vi.mocked(fetch).mockResolvedValue(new Response('{}',{status:200}));render(<MemoryRouter initialEntries={['/privacy-session']}><Routes><Route path="/" element={<Index/>}/><Route path="/privacy-session" element={<PrivacySession/>}/></Routes></MemoryRouter>);await waitFor(()=>expect(screen.getByTestId('privacy-session-page')).toBeInTheDocument());fireEvent.click(screen.getByRole('button',{name:/continue to landing/i}));await waitFor(()=>expect(screen.getByTestId('landing-page')).toBeInTheDocument());});
  it('renders direct Privacy after the tab has seen the session',async()=>{sessionStorage.setItem('healsense_privacy_seen','1');vi.mocked(fetch).mockResolvedValue(new Response('{}',{status:200}));render(<MemoryRouter initialEntries={['/privacy-session']}><PrivacySession/></MemoryRouter>);expect(await screen.findByTestId('privacy-session-page')).toBeInTheDocument();});
});
