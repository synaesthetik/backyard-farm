import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import HealthBadge from './HealthBadge.svelte';
import type { HealthScore } from './types';

afterEach(() => cleanup());

describe('HealthBadge', () => {
  it('renders "GOOD" for green score', () => {
    render(HealthBadge, { score: 'green' as HealthScore });
    expect(screen.getByText('GOOD')).toBeTruthy();
  });

  it('renders "WARN" for yellow score', () => {
    render(HealthBadge, { score: 'yellow' as HealthScore });
    expect(screen.getByText('WARN')).toBeTruthy();
  });

  it('renders "CRIT" for red score', () => {
    render(HealthBadge, { score: 'red' as HealthScore });
    expect(screen.getByText('CRIT')).toBeTruthy();
  });

  it('has aria-label for green score', () => {
    const { container } = render(HealthBadge, { score: 'green' as HealthScore });
    const badge = container.querySelector('[aria-label]');
    expect(badge?.getAttribute('aria-label')).toBe('Zone health: Good');
  });

  it('has aria-label for yellow score', () => {
    const { container } = render(HealthBadge, { score: 'yellow' as HealthScore });
    const badge = container.querySelector('[aria-label]');
    expect(badge?.getAttribute('aria-label')).toBe('Zone health: Warning');
  });

  it('has aria-label for red score', () => {
    const { container } = render(HealthBadge, { score: 'red' as HealthScore });
    const badge = container.querySelector('[aria-label]');
    expect(badge?.getAttribute('aria-label')).toBe('Zone health: Critical');
  });
});
