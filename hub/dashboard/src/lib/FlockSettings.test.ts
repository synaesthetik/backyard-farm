import { describe, it, expect, afterEach, vi, beforeEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/svelte';
import FlockSettings from './FlockSettings.svelte';

// Mock $app/navigation
vi.mock('$app/navigation', () => ({
  goto: vi.fn(),
}));

// Mock $lib/ws.svelte
vi.mock('$lib/ws.svelte', () => ({
  dashboardStore: {
    eggCount: null,
  },
}));

// Default mock: GET /api/flock/config returns a valid config
function mockFetchConfig(overrides: Record<string, unknown> = {}) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            breed: 'Rhode Island Red',
            lay_rate_override: null,
            hatch_date: '2024-01-01',
            flock_size: 6,
            supplemental_lighting: false,
            tare_weight_grams: 0,
            hen_weight_threshold_grams: 1500,
            egg_weight_grams: 60,
            latitude: 0,
            longitude: 0,
            ...overrides,
          }),
      })
    )
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('FlockSettings', () => {
  it('renders loading skeleton initially', () => {
    // Never resolving fetch — stays in loading state
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));

    render(FlockSettings);

    const skeleton = document.querySelector('.form-skeleton');
    expect(skeleton).toBeTruthy();
    expect(skeleton?.getAttribute('aria-busy')).toBe('true');
  });

  it('renders breed select with 11 options (10 breeds + Custom)', async () => {
    mockFetchConfig();

    render(FlockSettings);

    const select = await vi.waitFor(() => {
      const el = document.querySelector('#breed') as HTMLSelectElement | null;
      if (!el) throw new Error('Select not found yet');
      return el;
    }, { timeout: 2000 });

    expect(select.options.length).toBe(11);

    const optionTexts = Array.from(select.options).map((o) => o.text);
    expect(optionTexts).toContain('Custom');
    expect(optionTexts).toContain('Rhode Island Red');
    expect(optionTexts).toContain('Leghorn');
  });

  it('selecting "Custom" breed shows lay rate input field', async () => {
    mockFetchConfig({ breed: 'Custom', lay_rate_override: 0.75 });

    render(FlockSettings);

    await vi.waitFor(() => {
      const input = document.querySelector('#layRateOverride');
      if (!input) throw new Error('lay rate input not found');
      return input;
    }, { timeout: 2000 });

    const layRateInput = document.querySelector('#layRateOverride');
    expect(layRateInput).toBeTruthy();
  });

  it('selecting a non-Custom breed hides lay rate input field', async () => {
    mockFetchConfig({ breed: 'Leghorn', lay_rate_override: null });

    render(FlockSettings);

    // Wait for form to load (skeleton gone)
    await vi.waitFor(() => {
      const skeleton = document.querySelector('.form-skeleton');
      if (skeleton) throw new Error('Still loading');
      return true;
    }, { timeout: 2000 });

    const layRateInput = document.querySelector('#layRateOverride');
    expect(layRateInput).toBeNull();
  });

  it('flock_size=0 shows validation error "Flock size must be at least 1."', async () => {
    // Load config with flock_size already 0 — Svelte binds value on load
    mockFetchConfig({ flock_size: 0 });

    render(FlockSettings);

    // Wait for form to appear
    await vi.waitFor(() => {
      const select = document.querySelector('#breed');
      if (!select) throw new Error('Form not loaded yet');
      return select;
    }, { timeout: 2000 });

    // flock_size is 0 from the mocked config — submitting form triggers validation
    const form = document.querySelector('form');
    expect(form).toBeTruthy();
    fireEvent.submit(form!);

    await vi.waitFor(() => {
      const error = screen.queryByText('Flock size must be at least 1.');
      if (!error) throw new Error('Validation error not shown');
      return error;
    }, { timeout: 2000 });

    expect(screen.getByText('Flock size must be at least 1.')).toBeTruthy();
  });

  it('Save button has aria-label="Save flock settings"', async () => {
    mockFetchConfig();

    render(FlockSettings);

    // Wait for form to appear — save button visible in both loading and loaded states
    // (button is inside form, not shown during skeleton)
    await vi.waitFor(() => {
      const btn = document.querySelector('[aria-label="Save flock settings"]');
      if (!btn) throw new Error('Save button not found');
      return btn;
    }, { timeout: 2000 });

    const saveBtn = document.querySelector('[aria-label="Save flock settings"]');
    expect(saveBtn).toBeTruthy();
    expect(saveBtn?.getAttribute('aria-label')).toBe('Save flock settings');
  });
});
