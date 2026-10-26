import {beforeEach,describe,expect,it,vi} from 'vitest';
import {render,screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import Index from '@/pages/Index';
import {patientApi} from '@/lib/api';

const {useAuth}=vi.hoisted(()=>({useAuth:vi.fn()}));
vi.mock('@/contexts/AuthContext',()=>({useAuth}));

const renderLanding=()=>render(<MemoryRouter><Index/></MemoryRouter>);
beforeEach(()=>{sessionStorage.setItem('healsense_privacy_seen','1');useAuth.mockReturnValue({isAuthenticated:false,isLoading:false});vi.clearAllMocks();useAuth.mockReturnValue({isAuthenticated:false,isLoading:false});});

describe('HealSense landing page',()=>{
  it('shows unauthenticated sign-in and create-account routes',()=>{renderLanding();expect(screen.getAllByRole('link',{name:/sign in/i})[0]).toHaveAttribute('href','/login');expect(screen.getAllByRole('link',{name:/create account/i})[0]).toHaveAttribute('href','/signup');});
  it('shows authenticated dashboard and cockpit routes',()=>{useAuth.mockReturnValue({isAuthenticated:true,isLoading:false});renderLanding();expect(screen.getAllByRole('link',{name:/telemetry dashboard/i}).some(link=>link.getAttribute('href')==='/dashboard')).toBe(true);expect(screen.getAllByRole('link',{name:/3d specimen cockpit/i}).some(link=>link.getAttribute('href')==='/cockpit?mode=live')).toBe(true);});
  it('labels the sample and renders FAQ/disclaimer copy',()=>{renderLanding();expect(screen.getByText(/illustrative telemetry preview/i)).toBeInTheDocument();expect(screen.getAllByText(/sample/i).length).toBeGreaterThan(0);expect(screen.getByText(/does healsense replace my doctor/i)).toBeInTheDocument();expect(screen.getByText(/for emergencies, contact local emergency services/i)).toBeInTheDocument();});
  it('does not call patient APIs while rendering',()=>{const profile=vi.spyOn(patientApi,'getProfile');renderLanding();expect(profile).not.toHaveBeenCalled();});
});
