import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import AISettingsToggle from './AISettingsToggle.svelte';
import type { ModelMaturityEntry, AIDomain } from './types';

afterEach(() => cleanup());

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

describe('AISettingsToggle', () => {
  it('renders domain label text for irrigation', () => {
    render(AISettingsToggle, { domain: 'irrigation', entry: makeEntry() });
    expect(screen.getByText('Irrigation Recommendations')).toBeTruthy();
  });

  it('renders description text for irrigation', () => {
    render(AISettingsToggle, { domain: 'irrigation', entry: makeEntry() });
    expect(
      screen.getByText('ONNX model optimizes irrigation timing based on soil moisture patterns.')
    ).toBeTruthy();
  });

  it('toggle has role="switch"', () => {
    render(AISettingsToggle, { domain: 'irrigation', entry: makeEntry() });
    expect(screen.getByRole('switch')).toBeTruthy();
  });

  it('toggle shows aria-checked="false" when mode is "rules"', () => {
    render(AISettingsToggle, { domain: 'irrigation', entry: makeEntry({ mode: 'rules' }) });
    const toggle = screen.getByRole('switch');
    expect(toggle.getAttribute('aria-checked')).toBe('false');
  });

  it('toggle is aria-disabled="true" when gate_passed is false (not mature)', () => {
    render(AISettingsToggle, { domain: 'irrigation', entry: makeEntry({ gate_passed: false }) });
    const toggle = screen.getByRole('switch');
    expect(toggle.getAttribute('aria-disabled')).toBe('true');
  });

  it('toggle has title="Model not yet mature" when disabled', () => {
    render(AISettingsToggle, { domain: 'irrigation', entry: makeEntry({ gate_passed: false }) });
    const toggle = screen.getByRole('switch');
    expect(toggle.getAttribute('title')).toBe('Model not yet mature');
  });

  it('toggle has opacity style when disabled', () => {
    render(AISettingsToggle, { domain: 'irrigation', entry: makeEntry({ gate_passed: false }) });
    const toggle = screen.getByRole('switch');
    expect(toggle.getAttribute('style')).toContain('opacity: 0.5');
  });
});
