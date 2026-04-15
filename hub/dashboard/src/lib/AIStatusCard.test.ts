import { describe, it, expect, afterEach, vi, beforeEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import AIStatusCard from './AIStatusCard.svelte';
import type { ModelMaturityEntry } from './types';

afterEach(() => cleanup());

// Mock the dashboardStore
vi.mock('./ws.svelte', () => {
  let modelMaturity: ModelMaturityEntry[] | null = null;

  return {
    dashboardStore: {
      get modelMaturity() {
        return modelMaturity;
      },
      _setModelMaturity(val: ModelMaturityEntry[] | null) {
        modelMaturity = val;
      },
    },
  };
});

function makeEntry(overrides: Partial<ModelMaturityEntry> = {}): ModelMaturityEntry {
  return {
    domain: 'irrigation',
    mode: 'rules',
    weeks_of_data: 2,
    good_flag_ratio: 0.9,
    recommendation_count: 10,
    approved_count: 8,
    rejected_count: 2,
    gate_passed: false,
    ...overrides,
  };
}

describe('AIStatusCard', () => {
  beforeEach(async () => {
    const { dashboardStore } = await import('./ws.svelte');
    (dashboardStore as any)._setModelMaturity(null);
  });

  it('renders "AI Engine" heading', async () => {
    const { dashboardStore } = await import('./ws.svelte');
    (dashboardStore as any)._setModelMaturity([makeEntry()]);
    render(AIStatusCard);
    expect(screen.getByText('AI Engine')).toBeTruthy();
  });

  it('renders cold-start message when entries have gate_passed=false', async () => {
    const { dashboardStore } = await import('./ws.svelte');
    (dashboardStore as any)._setModelMaturity([
      makeEntry({ gate_passed: false }),
    ]);
    render(AIStatusCard);
    expect(
      screen.getByText('The AI is still learning — rule-based recommendations are active.')
    ).toBeTruthy();
  });

  it('renders "Mature" text when entry has gate_passed=true', async () => {
    const { dashboardStore } = await import('./ws.svelte');
    (dashboardStore as any)._setModelMaturity([
      makeEntry({ gate_passed: true, weeks_of_data: 4, mode: 'ai' }),
    ]);
    render(AIStatusCard);
    // When all mature, compact mode — no progress bars, shows compact summary
    expect(screen.getByText('AI Engine')).toBeTruthy();
    expect(screen.queryByText('The AI is still learning — rule-based recommendations are active.')).toBeNull();
  });

  it('renders correct approval rate when recommendation_count > 0', async () => {
    const { dashboardStore } = await import('./ws.svelte');
    (dashboardStore as any)._setModelMaturity([
      makeEntry({ recommendation_count: 10, approved_count: 8, gate_passed: false }),
    ]);
    render(AIStatusCard);
    expect(screen.getByText('80% approved')).toBeTruthy();
  });

  it('renders "Configure AI" link with href="/settings/ai"', async () => {
    const { dashboardStore } = await import('./ws.svelte');
    (dashboardStore as any)._setModelMaturity([makeEntry()]);
    render(AIStatusCard);
    const link = screen.getByRole('link', { name: 'Configure AI' });
    expect(link).toBeTruthy();
    expect(link.getAttribute('href')).toBe('/settings/ai');
  });

  it('does NOT render progress bars when all domains are mature (compact mode)', async () => {
    const { dashboardStore } = await import('./ws.svelte');
    (dashboardStore as any)._setModelMaturity([
      makeEntry({ domain: 'irrigation', gate_passed: true, weeks_of_data: 4, mode: 'ai' }),
      makeEntry({ domain: 'zone_health', gate_passed: true, weeks_of_data: 4, mode: 'ai' }),
      makeEntry({ domain: 'flock_anomaly', gate_passed: true, weeks_of_data: 4, mode: 'ai' }),
    ]);
    render(AIStatusCard);
    const progressBars = document.querySelectorAll('[role="progressbar"]');
    expect(progressBars.length).toBe(0);
  });
});
