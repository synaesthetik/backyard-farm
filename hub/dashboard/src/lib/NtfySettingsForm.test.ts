import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import NtfySettingsForm from './NtfySettingsForm.svelte';
import type { NtfySettings } from './types';

afterEach(() => cleanup());

const defaultSettings: NtfySettings = { url: '', topic: '', enabled: false };

describe('NtfySettingsForm', () => {
  it('test_renders_url_and_topic_inputs', () => {
    render(NtfySettingsForm, {
      settings: defaultSettings,
      onsave: vi.fn(),
      ontest: vi.fn(),
    });
    expect(screen.getByLabelText('ntfy Server URL')).toBeTruthy();
    expect(screen.getByLabelText('Topic')).toBeTruthy();
  });

  it('test_renders_send_test_button', () => {
    render(NtfySettingsForm, {
      settings: defaultSettings,
      onsave: vi.fn(),
      ontest: vi.fn(),
    });
    expect(screen.getByText('Send Test')).toBeTruthy();
  });

  it('test_renders_save_button', () => {
    render(NtfySettingsForm, {
      settings: defaultSettings,
      onsave: vi.fn(),
      ontest: vi.fn(),
    });
    expect(screen.getByText('Save Settings')).toBeTruthy();
  });

  it('test_renders_empty_state_when_disabled', () => {
    render(NtfySettingsForm, {
      settings: { url: '', topic: '', enabled: false },
      onsave: vi.fn(),
      ontest: vi.fn(),
    });
    expect(screen.getByText(/Push notifications are off/)).toBeTruthy();
  });
});
