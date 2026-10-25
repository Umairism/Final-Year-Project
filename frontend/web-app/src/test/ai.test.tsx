import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { aiApi } from '@/lib/api';
import { SafeMarkdown } from '@/lib/safeMarkdown';
import { PatientAssistantPanel } from '@/components/ai/PatientAssistantPanel';
import { GeminiExplanationCard } from '@/components/risk/GeminiExplanationCard';

afterEach(() => { cleanup(); vi.restoreAllMocks(); });
const wrap = (children: React.ReactNode) => <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{children}</QueryClientProvider>;

describe('AI helpers and safe rendering', () => {
  it('renders markdown-like safe text without creating scripts', () => {
    const { container } = render(<SafeMarkdown text={'### Heading\n- **Bold** item\n<script>alert(1)</script>'} />);
    expect(screen.getByText('Heading')).toBeInTheDocument();
    expect(screen.getByText('Bold')).toBeInTheDocument();
    expect(container.querySelector('script')).toBeNull();
    expect(container.textContent).toContain('<script>alert(1)</script>');
  });

  it('maps AI error classes without exposing raw details', async () => {
    vi.spyOn(aiApi, 'getProviders').mockResolvedValue({ openai: { configured: false, model: 'x' }, gemini: { configured: true, model: 'm' } });
    vi.spyOn(aiApi, 'askPatientAssistant').mockRejectedValue(Object.assign(new Error('raw'), { status: 502, detail: { error: 'gemini_upstream_error', raw: 'secret' } }));
    render(wrap(<PatientAssistantPanel patientId="P001" />));
    const input = await screen.findByPlaceholderText(/Ask about/); fireEvent.change(input, { target: { value: 'test' } }); fireEvent.click(screen.getByText('Send'));
    await waitFor(() => expect(screen.getByText(/Gemini is temporarily unavailable/)).toBeInTheDocument());
  });
});

describe('PatientAssistantPanel', () => {
  const provider = { openai: { configured: false, model: 'x' }, gemini: { configured: true, model: 'gemini-test' } };
  it('disables assistant when Gemini is not configured', async () => {
    vi.spyOn(aiApi, 'getProviders').mockResolvedValue({ ...provider, gemini: { configured: false, model: 'gemini-test' } });
    render(wrap(<PatientAssistantPanel patientId="P001" />));
    await waitFor(() => expect(screen.getByText(/not configured/)).toBeInTheDocument());
    expect(screen.queryByText('Send')).not.toBeInTheDocument();
  });

  it('sends a suggestion and renders answer metadata', async () => {
    vi.spyOn(aiApi, 'getProviders').mockResolvedValue(provider);
    const ask = vi.spyOn(aiApi, 'askPatientAssistant').mockResolvedValue({ patient_id: 'P001', answer: '**OK**', model: 'gemini-test', data_as_of: '2026-01-01T00:00:00Z', data_freshness_seconds: 12, latest_status: 'critical', is_simulated_data: true, disclaimer: 'Decision support only' });
    render(wrap(<PatientAssistantPanel patientId="P001" />));
    const chip = await screen.findByText("Summarize the patient's current status."); fireEvent.click(chip);
    await waitFor(() => expect(screen.getByText('OK')).toBeInTheDocument());
    expect(ask).toHaveBeenCalledWith(expect.objectContaining({ patient_id: 'P001', message: "Summarize the patient's current status.", conversation: [] }));
    expect(screen.getByText('Simulated/Seeded')).toBeInTheDocument();
    expect(screen.getByText('Decision support only')).toBeInTheDocument();
  });

  it('keeps the user message and retries without fabricating an answer', async () => {
    vi.spyOn(aiApi, 'getProviders').mockResolvedValue(provider);
    const ask = vi.spyOn(aiApi, 'askPatientAssistant').mockRejectedValueOnce(Object.assign(new Error(), { status: 502 })).mockResolvedValueOnce({ patient_id: 'P001', answer: 'Recovered', model: 'm', data_as_of: '2026-01-01', data_freshness_seconds: 1, latest_status: 'normal', is_simulated_data: false, disclaimer: 'safe' });
    render(wrap(<PatientAssistantPanel patientId="P001" />));
    const input = await screen.findByPlaceholderText(/Ask about/); fireEvent.change(input, { target: { value: 'question' } }); fireEvent.click(screen.getByText('Send'));
    await waitFor(() => expect(screen.getByText(/temporarily unavailable/)).toBeInTheDocument());
    expect(screen.getByText('question')).toBeInTheDocument(); expect(screen.queryByText('Recovered')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Retry last question')); await waitFor(() => expect(screen.getByText('Recovered')).toBeInTheDocument()); expect(ask).toHaveBeenCalledTimes(2);
  });

  it('clears transcript and metadata', async () => {
    vi.spyOn(aiApi, 'getProviders').mockResolvedValue(provider);
    vi.spyOn(aiApi, 'askPatientAssistant').mockResolvedValue({ patient_id: 'P001', answer: 'Answer', model: 'm', data_as_of: '2026-01-01', data_freshness_seconds: 1, latest_status: 'normal', is_simulated_data: false, disclaimer: 'safe' });
    render(wrap(<PatientAssistantPanel patientId="P001" />)); await screen.findByText("Summarize the patient's current status."); fireEvent.click(screen.getByText("Summarize the patient's current status.")); await waitFor(() => expect(screen.getByText('Answer')).toBeInTheDocument()); fireEvent.click(screen.getByText('Clear chat')); expect(screen.queryByText('Answer')).not.toBeInTheDocument();
  });
});

describe('GeminiExplanationCard', () => {
  it('renders loading, success metadata, stale hint, and error retry', () => {
    const retry = vi.fn(); const { rerender } = render(<GeminiExplanationCard loading timestamp={new Date()} />); expect(screen.getByText(/Generating/)).toBeInTheDocument();
    rerender(<GeminiExplanationCard explanation="### Reason" level="critical" confidence={0.9} explainedAt={new Date()} newerReading onRetry={retry} />); expect(screen.getByText('Reason')).toBeInTheDocument(); expect(screen.getByText(/Final risk/)).toBeInTheDocument(); expect(screen.getByText(/Newer reading/)).toBeInTheDocument();
    rerender(<GeminiExplanationCard error={Object.assign(new Error(), { status: 502 })} onRetry={retry} />); expect(screen.getByText(/temporarily unavailable/)).toBeInTheDocument(); fireEvent.click(screen.getByText('Retry')); expect(retry).toHaveBeenCalled();
  });
});
