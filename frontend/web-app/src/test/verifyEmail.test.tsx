import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import VerifyEmail from '@/pages/VerifyEmail';
import { authApi } from '@/lib/api';

vi.mock('@/contexts/AuthContext',()=>({useAuth:()=>({resendVerification:vi.fn().mockResolvedValue({success:true})})}));
beforeEach(()=>vi.restoreAllMocks());
describe('VerifyEmail',()=>{
 it('calls verification once and shows continue CTA',async()=>{const call=vi.spyOn(authApi,'verifyEmail').mockResolvedValue({verified:true,email:'u@example.com'});render(<MemoryRouter initialEntries={['/verify-email?token=secret-token']}><VerifyEmail/></MemoryRouter>);await waitFor(()=>expect(screen.getByText('Continue to login')).toBeInTheDocument());expect(call).toHaveBeenCalledTimes(1);expect(document.body.textContent).not.toContain('secret-token');});
 it('shows resend state for an invalid link',async()=>{vi.spyOn(authApi,'verifyEmail').mockRejectedValue({status:400,detail:{error:'invalid_or_expired_token'}});render(<MemoryRouter initialEntries={['/verify-email?token=bad']}><VerifyEmail/></MemoryRouter>);await waitFor(()=>expect(screen.getByText('Resend verification')).toBeInTheDocument());});
});
