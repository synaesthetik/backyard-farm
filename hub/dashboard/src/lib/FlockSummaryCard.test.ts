import { describe, it, expect, afterEach, vi, beforeEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import FlockSummaryCard from './FlockSummaryCard.svelte';

// Mock the ws.svelte store
vi.mock('$lib/ws.svelte', () => {
  return {
    dashboardStore: {
      eggCount: null,
      actuatorStates: new Map(),
      feedConsumption: null,
    },
  };
});

// Mock $app/navigation
vi.mock('$app/navigation', () => ({
  goto: vi.fn(),
}));

afterEach(() => cleanup());

describe('FlockSummaryCard', () => {
  it('renders with null eggCount showing "--"', async () => {
    const { dashboardStore } = await import('$lib/ws.svelte');
    (dashboardStore as any).eggCount = null;
    (dashboardStore as any).actuatorStates = new Map([['coop_door', 'closed']]);

    render(FlockSummaryCard);
    expect(screen.getByText('--')).toBeTruthy();
  });

  it('renders with eggCount showing "N eggs today"', async () => {
    const { dashboardStore } = await import('$lib/ws.svelte');
    (dashboardStore as any).eggCount = {
      today: 5,
      hen_present: false,
      raw_weight_grams: null,
      updated_at: new Date().toISOString(),
    };
    (dashboardStore as any).actuatorStates = new Map([['coop_door', 'open']]);

    render(FlockSummaryCard);
    expect(screen.getByText('5 eggs today')).toBeTruthy();
  });

  it('has role="button" and aria-label', () => {
    render(FlockSummaryCard);
    const card = screen.getByRole('button');
    expect(card).toBeTruthy();
    expect(card.getAttribute('aria-label')).toBe(
      'Flock summary — tap to see coop detail'
    );
  });

  it('shows door state badge', async () => {
    const { dashboardStore } = await import('$lib/ws.svelte');
    (dashboardStore as any).actuatorStates = new Map([['coop_door', 'open']]);

    render(FlockSummaryCard);
    expect(screen.getByText('OPEN')).toBeTruthy();
  });
});
