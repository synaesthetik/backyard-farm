import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import AlertBar from './AlertBar.svelte';
import type { AlertEntry } from './types';

// $app/navigation is aliased to src/__mocks__/navigation.ts via vitest.config.ts

afterEach(() => cleanup());

function makeAlert(overrides: Partial<AlertEntry> = {}): AlertEntry {
  return {
    key: 'low_moisture:raised-bed-1',
    severity: 'P1',
    message: 'Low moisture — Zone A',
    deep_link: '/',
    count: 1,
    ...overrides,
  };
}

describe('AlertBar', () => {
  it('renders P0 alert row with red severity bar', () => {
    const alerts = [
      makeAlert({ key: 'stuck_door:coop', severity: 'P0', message: 'Coop door stuck', deep_link: '/coop' }),
    ];
    const { container } = render(AlertBar, { alerts });
    const row = container.querySelector('.alert-row.p0');
    expect(row).not.toBeNull();
    expect(screen.getByText('Coop door stuck')).toBeTruthy();
  });

  it('renders P1 alert row with amber severity bar', () => {
    const alerts = [makeAlert({ severity: 'P1', message: 'Low moisture — Zone A' })];
    const { container } = render(AlertBar, { alerts });
    const row = container.querySelector('.alert-row.p1');
    expect(row).not.toBeNull();
    expect(screen.getByText('Low moisture — Zone A')).toBeTruthy();
  });

  it('shows count badge when count > 1', () => {
    const alerts = [makeAlert({ message: 'Low moisture — 3 zones', count: 3 })];
    render(AlertBar, { alerts });
    // count badge renders the count number
    expect(screen.getByText('3')).toBeTruthy();
  });

  it('does not render count badge when count is 1', () => {
    const alerts = [makeAlert({ count: 1 })];
    const { container } = render(AlertBar, { alerts });
    const badge = container.querySelector('.count-badge');
    expect(badge).toBeNull();
  });

  it('renders nothing when alerts array is empty', () => {
    const { container } = render(AlertBar, { alerts: [] });
    expect(container.querySelector('.alert-bar')).toBeNull();
  });

  it('alert row has role button (is tappable)', () => {
    const alerts = [makeAlert()];
    const { container } = render(AlertBar, { alerts });
    // The alert rows are <button> elements — role="button" by default
    const btn = container.querySelector('button.alert-row');
    expect(btn).not.toBeNull();
  });
});
