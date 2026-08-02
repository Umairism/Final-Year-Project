import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { HeartRateCard } from '../components/vitals/HeartRateCard';
import { BloodPressureCard } from '../components/vitals/BloodPressureCard';
import { RiskGauge } from '../components/risk/RiskGauge';

describe('Phase 4 Frontend Clinical Components', () => {
  it('renders HeartRateCard correctly', () => {
    render(<HeartRateCard heartRate={78} status="normal" delayedSync={true} />);
    expect(screen.getByText('Heart Rate')).toBeInTheDocument();
    expect(screen.getByText('78')).toBeInTheDocument();
    expect(screen.getByText('Delayed Sync')).toBeInTheDocument();
  });

  it('renders BloodPressureCard with source badge', () => {
    render(<BloodPressureCard systolic={120} diastolic={80} bpSource="ble_cuff" status="normal" />);
    expect(screen.getByText('120/80')).toBeInTheDocument();
    expect(screen.getByText('Source: BLE Cuff')).toBeInTheDocument();
  });

  it('renders RiskGauge with critical warning status', () => {
    render(<RiskGauge status="critical" score={0.92} deterministicFlags={['SpO2 < 92% (Hypoxia Risk)']} />);
    expect(screen.getByText(/critical/i)).toBeInTheDocument();
    expect(screen.getByText('0.92')).toBeInTheDocument();
    expect(screen.getByText('SpO2 < 92% (Hypoxia Risk)')).toBeInTheDocument();
  });
});
