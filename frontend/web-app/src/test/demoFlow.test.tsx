import {describe,expect,it,vi} from 'vitest';
import {MemoryRouter} from 'react-router-dom';
import {render,screen} from '@testing-library/react';
import DemoFlowStrip from '@/components/landing/DemoFlowStrip';
import {cockpitSearchParams,currentDemoStep,parseCockpitQuery} from '@/lib/demoFlow';

vi.mock('@/contexts/AuthContext',()=>({useAuth:()=>({isAuthenticated:false,user:null})}));

describe('clinical demo flow',()=>{
  it('parses valid and ignores invalid cockpit parameters',()=>{expect(parseCockpitQuery('?mode=simulation&scenario=hypoxia')).toEqual({mode:'simulation',scenario:'hypoxia'});expect(parseCockpitQuery('?mode=simulation&scenario=unknown')).toEqual({mode:'simulation',scenario:'stable'});expect(parseCockpitQuery('?mode=invalid&scenario=hypoxia')).toEqual({mode:'live'});expect(cockpitSearchParams({mode:'live'})).toEqual({mode:'live'});expect(cockpitSearchParams({mode:'simulation',scenario:'hypoxia'})).toEqual({mode:'simulation',scenario:'hypoxia'});});
  it('selects current steps for public and cockpit routes',()=>{expect(currentDemoStep('/privacy-session')).toBe(1);expect(currentDemoStep('/')).toBe(2);expect(currentDemoStep('/login')).toBe(3);expect(currentDemoStep('/cockpit','?mode=live')).toBe(5);expect(currentDemoStep('/cockpit','?mode=simulation&scenario=hypoxia')).toBe(6);});
  it('renders seven real flow links',()=>{render(<MemoryRouter><DemoFlowStrip/></MemoryRouter>);const links=screen.getAllByRole('link');expect(links.map(link=>link.getAttribute('href'))).toEqual(['/privacy-session','/','/login','/dashboard','/cockpit?mode=live','/cockpit?mode=simulation&scenario=hypoxia','/cockpit?mode=live']);});
});
