import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/svelte';
import StoragePanel from './StoragePanel.svelte';
import type { StorageStats } from './types';

afterEach(() => cleanup());

const mockStats: StorageStats = {
  tables: [
    { tablename: 'sensor_readings', size: '1.2 GB', size_bytes: 1200000000 },
    { tablename: 'hourly_rollups', size: '256 MB', size_bytes: 256000000 },
  ],
  retention_policies: [],
  total_size: '1.5 GB',
  total_bytes: 1500000000,
};

describe('StoragePanel', () => {
  it('test_renders_table_sizes', () => {
    render(StoragePanel, { stats: mockStats, onpurge: vi.fn() });
    expect(screen.getByText('sensor_readings')).toBeTruthy();
    expect(screen.getByText('1.2 GB')).toBeTruthy();
  });

  it('test_renders_purge_button', () => {
    render(StoragePanel, { stats: mockStats, onpurge: vi.fn() });
    expect(screen.getByText('Purge Now')).toBeTruthy();
  });

  it('test_shows_confirmation_on_purge_click', async () => {
    render(StoragePanel, { stats: mockStats, onpurge: vi.fn() });
    const purgeBtn = screen.getByText('Purge Now');
    await fireEvent.click(purgeBtn);
    expect(screen.getByText(/This will permanently delete/)).toBeTruthy();
  });

  it('test_hides_confirmation_on_keep_data', async () => {
    render(StoragePanel, { stats: mockStats, onpurge: vi.fn() });
    const purgeBtn = screen.getByText('Purge Now');
    await fireEvent.click(purgeBtn);
    const keepBtn = screen.getByText('Keep My Data');
    await fireEvent.click(keepBtn);
    expect(screen.queryByText(/This will permanently delete/)).toBeNull();
  });
});
