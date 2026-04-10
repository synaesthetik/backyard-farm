import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import CommandButton from './CommandButton.svelte';

afterEach(() => cleanup());

describe('CommandButton', () => {
  it('shows label text when idle', () => {
    render(CommandButton, { label: 'Open valve' });
    expect(screen.getByText('Open valve')).toBeTruthy();
  });

  it('hides label and shows spinner when loading=true', () => {
    render(CommandButton, { label: 'Open valve', loading: true });
    expect(screen.queryByText('Open valve')).toBeNull();
    const { container } = render(CommandButton, { label: 'Open valve', loading: true });
    expect(container.querySelector('.spinner')).not.toBeNull();
  });

  it('has aria-disabled when loading=true', () => {
    const { container } = render(CommandButton, { label: 'Open valve', loading: true });
    const btn = container.querySelector('button');
    expect(btn?.getAttribute('aria-disabled')).toBe('true');
  });

  it('has aria-busy when loading=true', () => {
    const { container } = render(CommandButton, { label: 'Open valve', loading: true });
    const btn = container.querySelector('button');
    expect(btn?.getAttribute('aria-busy')).toBe('true');
  });

  it('button is disabled when loading=true', () => {
    const { container } = render(CommandButton, { label: 'Open valve', loading: true });
    const btn = container.querySelector('button');
    expect(btn?.disabled).toBe(true);
  });

  it('approve variant has accent background class', () => {
    const { container } = render(CommandButton, { label: 'Approve', variant: 'approve' });
    const btn = container.querySelector('button');
    expect(btn?.classList.contains('approve')).toBe(true);
  });

  it('is not disabled when idle', () => {
    const { container } = render(CommandButton, { label: 'Open valve' });
    const btn = container.querySelector('button');
    expect(btn?.disabled).toBe(false);
  });
});
