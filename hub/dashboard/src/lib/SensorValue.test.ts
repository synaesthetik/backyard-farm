import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import SensorValue from './SensorValue.svelte';
import { Droplets } from 'lucide-svelte';

afterEach(() => cleanup());

describe('SensorValue', () => {
  it('renders value with unit', () => {
    render(SensorValue, {
      icon: Droplets,
      label: 'Moisture',
      value: 45.3,
      unit: '%',
      quality: 'GOOD',
    });
    expect(screen.getByText('45.3%')).toBeTruthy();
  });

  it('renders "--" when value is null', () => {
    render(SensorValue, {
      icon: Droplets,
      label: 'Moisture',
      value: null,
      unit: '%',
      quality: null,
    });
    expect(screen.getByText('--')).toBeTruthy();
  });

  it('renders GOOD quality badge', () => {
    render(SensorValue, {
      icon: Droplets,
      label: 'Moisture',
      value: 45.3,
      unit: '%',
      quality: 'GOOD',
    });
    expect(screen.getByText('GOOD')).toBeTruthy();
  });

  it('renders SUSPECT quality badge', () => {
    render(SensorValue, {
      icon: Droplets,
      label: 'Moisture',
      value: 45.3,
      unit: '%',
      quality: 'SUSPECT',
    });
    expect(screen.getByText('SUSPECT')).toBeTruthy();
  });

  it('renders BAD quality badge', () => {
    render(SensorValue, {
      icon: Droplets,
      label: 'Moisture',
      value: 45.3,
      unit: '%',
      quality: 'BAD',
    });
    expect(screen.getByText('BAD')).toBeTruthy();
  });

  it('does not render quality badge when quality is null', () => {
    render(SensorValue, {
      icon: Droplets,
      label: 'Moisture',
      value: 45.3,
      unit: '%',
      quality: null,
    });
    expect(screen.queryByText('GOOD')).toBeNull();
    expect(screen.queryByText('SUSPECT')).toBeNull();
    expect(screen.queryByText('BAD')).toBeNull();
  });

  it('renders label text', () => {
    render(SensorValue, {
      icon: Droplets,
      label: 'Moisture',
      value: 45.3,
      unit: '%',
      quality: 'GOOD',
    });
    expect(screen.getByText('Moisture')).toBeTruthy();
  });

  it('rounds temperature to integer', () => {
    render(SensorValue, {
      icon: Droplets,
      label: 'Temp',
      value: 22.7,
      unit: '°C',
      quality: 'GOOD',
    });
    expect(screen.getByText('23°C')).toBeTruthy();
  });
});
