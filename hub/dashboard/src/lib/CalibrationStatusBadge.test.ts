import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import CalibrationStatusBadge from './CalibrationStatusBadge.svelte';

afterEach(() => cleanup());

describe('CalibrationStatusBadge', () => {
  it('test_renders_overdue_when_null', () => {
    render(CalibrationStatusBadge, { days_since: null });
    expect(screen.getByText('OVERDUE')).toBeTruthy();
  });

  it('test_renders_overdue_when_over_14', () => {
    render(CalibrationStatusBadge, { days_since: 16 });
    expect(screen.getByText('OVERDUE')).toBeTruthy();
  });

  it('test_renders_due_soon_when_12_to_14', () => {
    render(CalibrationStatusBadge, { days_since: 13 });
    expect(screen.getByText('Due in 1 days')).toBeTruthy();
  });

  it('test_renders_calibrated_when_recent', () => {
    render(CalibrationStatusBadge, { days_since: 5 });
    expect(screen.getByText('Calibrated 5 days ago')).toBeTruthy();
  });
});
