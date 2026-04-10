import { describe, it, expect, afterEach, vi, beforeEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import ProductionChart from './ProductionChart.svelte';

// Mock uplot — it requires a real DOM canvas that jsdom doesn't support
vi.mock('uplot', () => {
  return {
    default: vi.fn().mockImplementation(() => ({
      destroy: vi.fn(),
      setSize: vi.fn(),
      height: 160,
    })),
  };
});

vi.mock('uplot/dist/uPlot.min.css', () => ({}));

// Mock ResizeObserver
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

afterEach(() => cleanup());

describe('ProductionChart', () => {
  it('renders loading skeleton initially', async () => {
    // Delay the fetch so we can catch the loading state
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise(() => {})) // never resolves
    );

    render(ProductionChart);

    const skeleton = document.querySelector('.skeleton');
    expect(skeleton).toBeTruthy();
    expect(skeleton?.getAttribute('aria-busy')).toBe('true');

    vi.unstubAllGlobals();
  });

  it('renders empty state message when data has fewer than 3 days', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              dates: ['2026-04-08', '2026-04-09'],
              actual: [3, 4],
              expected: [5, 5],
            }),
        })
      )
    );

    render(ProductionChart);

    // Wait for the async fetch + state update
    await vi.waitFor(
      () => {
        const msg = screen.queryByText(/Not enough data yet/);
        if (!msg) throw new Error('Message not found yet');
        return msg;
      },
      { timeout: 2000 }
    );

    expect(screen.getByText(/Not enough data yet/)).toBeTruthy();
    vi.unstubAllGlobals();
  });

  it('has correct aria-label on the container', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise(() => {})) // never resolves
    );

    render(ProductionChart);

    const container = document.querySelector('[aria-label]');
    expect(container).toBeTruthy();
    expect(container?.getAttribute('aria-label')).toContain('Egg production chart');
    expect(container?.getAttribute('aria-label')).toContain('actual vs expected');
    expect(container?.getAttribute('aria-label')).toContain('last 30 days');

    vi.unstubAllGlobals();
  });
});
