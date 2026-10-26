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
  it('shows authenticated dashboard and cockpit routes',()=>{useAuth.mockReturnValue({isAuthenticated:true,isLoading:false});renderLanding();expect(screen.getByRole('link',{name:/open dashboard/i})).toHaveAttribute('href','/dashboard');expect(screen.getByRole('link',{name:/open 3d cockpit/i})).toHaveAttribute('href','/cockpit?mode=live');});
  it('labels the sample and renders safety copy',()=>{renderLanding();expect(screen.getByText(/illustrative demo snapshot/i)).toBeInTheDocument();expect(screen.getByText(/not live patient data/i)).toBeInTheDocument();expect(screen.getByText(/how healsense works/i)).toBeInTheDocument();expect(screen.getByText(/for emergencies, contact local emergency services/i)).toBeInTheDocument();});
  it('does not call patient APIs while rendering',()=>{const profile=vi.spyOn(patientApi,'getProfile');renderLanding();expect(profile).not.toHaveBeenCalled();});
});
