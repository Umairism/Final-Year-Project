import { describe, expect, it, vi } from 'vitest'; import { fireEvent, render, screen } from '@testing-library/react'; import { MemoryRouter } from 'react-router-dom'; import Login from '@/pages/Login';
const login=vi.fn().mockResolvedValue({success:true});
vi.mock('@/contexts/AuthContext',()=>({useAuth:()=>({login,resendVerification:vi.fn()})}));
describe('demo login',()=>{it('submits the exact demo credentials immediately',async()=>{render(<MemoryRouter><Login/></MemoryRouter>);fireEvent.change(screen.getByLabelText('Email'),{target:{value:'other@example.com'}});fireEvent.change(screen.getByLabelText('Password'),{target:{value:'wrong'}});fireEvent.click(screen.getByRole('button',{name:'Use demo account'}));expect(login).toHaveBeenCalledWith('umair@healsense.com','password123');});});
