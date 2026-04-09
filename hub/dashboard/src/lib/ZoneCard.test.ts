import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import ZoneCard from './ZoneCard.svelte';
import type { ZoneState, SensorReading } from './types';

afterEach(() => cleanup());

function makeSensorReading(overrides: Partial<SensorReading> = {}): SensorReading {
  return {
    value: 42.0,
    quality: 'GOOD',
    stuck: false,
    received_at: new Date().toISOString(),
    ...overrides,
  };
}

function makeZone(overrides: Partial<ZoneState> = {}): ZoneState {
  return {
    zone_id: 'raised-bed-1',
    moisture: null,
    ph: null,
    temperature: null,
    ...overrides,
  };
}

describe('ZoneCard', () => {
  it('renders zone_id as heading text', () => {
    const { container } = render(ZoneCard, { zone: makeZone({ zone_id: 'raised-bed-1' }) });
    expect(screen.getByText('raised-bed-1')).toBeTruthy();
  });

  it('shows "No data received" when all sensor readings are null', () => {
    render(ZoneCard, { zone: makeZone() });
    expect(screen.getByText('No data received')).toBeTruthy();
  });

  it('renders sensor values when readings are provided', () => {
    const zone = makeZone({
      moisture: makeSensorReading({ value: 42.0, unit: '%' } as any),
      ph: makeSensorReading({ value: 6.5 }),
      temperature: makeSensorReading({ value: 20.0 }),
    });
    render(ZoneCard, { zone });
    // Moisture value formatted as X.X% (decimals=1 default)
    expect(screen.getByText('42.0%')).toBeTruthy();
  });

  it('applies .stale CSS class when received_at is older than 5 minutes', () => {
    const staleTimestamp = new Date(Date.now() - 600_000).toISOString(); // 10 minutes ago
    const zone = makeZone({
      moisture: makeSensorReading({ received_at: staleTimestamp }),
    });
    const { container } = render(ZoneCard, { zone });
    expect(container.querySelector('.zone-card.stale')).not.toBeNull();
  });

  it('shows "Stuck sensor detected" when any sensor has stuck=true', () => {
    const zone = makeZone({
      moisture: makeSensorReading({ stuck: true }),
    });
    render(ZoneCard, { zone });
    expect(screen.getByText('Stuck sensor detected')).toBeTruthy();
  });

  it('does not show stuck indicator when no sensors are stuck', () => {
    const zone = makeZone({
      moisture: makeSensorReading({ stuck: false }),
    });
    render(ZoneCard, { zone });
    expect(screen.queryByText('Stuck sensor detected')).toBeNull();
  });
});
