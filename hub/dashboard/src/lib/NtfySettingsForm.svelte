<script lang="ts">
  import type { NtfySettings } from './types';

  let {
    settings,
    onsave,
    ontest,
  }: {
    settings: NtfySettings;
    onsave: (settings: NtfySettings) => Promise<void>;
    ontest: () => Promise<boolean>;
  } = $props();

  let url = $state<string>(settings.url);
  let topic = $state<string>(settings.topic);
  let enabled = $state<boolean>(settings.enabled);

  // Sync internal state when settings prop changes
  $effect(() => {
    url = settings.url;
    topic = settings.topic;
    enabled = settings.enabled;
  });
  let testStatus = $state<'idle' | 'sending' | 'ok' | 'error'>('idle');
  let saveLoading = $state(false);

  const showEmptyState = $derived(!enabled && url === '');

  async function handleSave() {
    saveLoading = true;
    try {
      await onsave({ url, topic, enabled });
      window.dispatchEvent(new CustomEvent('farm:toast', {
        detail: { message: 'Notification settings saved' },
      }));
    } catch {
      window.dispatchEvent(new CustomEvent('farm:toast', {
        detail: { message: 'Settings update failed \u2014 check connection' },
      }));
    } finally {
      saveLoading = false;
    }
  }

  async function handleTest() {
    testStatus = 'sending';
    try {
      const ok = await ontest();
      testStatus = ok ? 'ok' : 'error';
      if (ok) {
        window.dispatchEvent(new CustomEvent('farm:toast', {
          detail: { message: 'Test notification sent \u2014 check your phone' },
        }));
      } else {
        window.dispatchEvent(new CustomEvent('farm:toast', {
          detail: { message: 'Test failed \u2014 verify ntfy URL and topic' },
        }));
      }
    } catch {
      testStatus = 'error';
      window.dispatchEvent(new CustomEvent('farm:toast', {
        detail: { message: 'Test failed \u2014 verify ntfy URL and topic' },
      }));
    } finally {
      if (testStatus !== 'idle') {
        setTimeout(() => { testStatus = 'idle'; }, 3000);
      }
    }
  }

  function toggleEnabled() {
    enabled = !enabled;
  }
</script>

<div class="ntfy-form">
  <div class="toggle-row">
    <div class="toggle-info">
      <span class="toggle-label">Push Notifications</span>
      <span class="toggle-description">Send alerts to your phone via ntfy when farm conditions need attention.</span>
    </div>
    <button
      class="toggle-switch"
      role="switch"
      aria-checked={enabled}
      aria-label="Push Notifications"
      onclick={toggleEnabled}
      type="button"
    >
      <span class="toggle-thumb" class:on={enabled}></span>
    </button>
  </div>

  {#if showEmptyState}
    <p class="empty-state">Push notifications are off. Enter your ntfy server URL and topic to enable.</p>
  {/if}

  <div class="field-group">
    <label for="ntfy-url">ntfy Server URL</label>
    <input
      id="ntfy-url"
      type="url"
      bind:value={url}
      placeholder="https://ntfy.sh"
      autocomplete="off"
    />
  </div>

  <div class="field-group">
    <label for="ntfy-topic">Topic</label>
    <input
      id="ntfy-topic"
      type="text"
      bind:value={topic}
      placeholder="my-farm-alerts"
      autocomplete="off"
    />
  </div>

  <div class="button-row">
    <button
      class="primary-btn"
      disabled={testStatus === 'sending'}
      aria-busy={testStatus === 'sending'}
      onclick={handleTest}
      type="button"
    >
      {testStatus === 'sending' ? 'Sending...' : 'Send Test'}
    </button>

    <button
      class="primary-btn"
      disabled={saveLoading}
      aria-busy={saveLoading}
      onclick={handleSave}
      type="button"
    >
      {saveLoading ? 'Saving...' : 'Save Settings'}
    </button>
  </div>
</div>

<style>
  .ntfy-form {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .toggle-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--spacing-md);
    min-height: 44px;
  }

  .toggle-info {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    flex: 1;
  }

  .toggle-label {
    font-size: 16px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-text-primary);
    line-height: 1.5;
  }

  .toggle-description {
    font-size: 14px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-muted);
    line-height: 1.4;
  }

  .toggle-switch {
    position: relative;
    width: 44px;
    height: 24px;
    border-radius: 12px;
    border: none;
    background: var(--color-border);
    cursor: pointer;
    flex-shrink: 0;
    padding: 0;
    min-height: 44px;
    min-width: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background var(--transition-base);
  }

  .toggle-switch[aria-checked="true"] {
    background: var(--color-accent);
  }

  .toggle-thumb {
    position: absolute;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: var(--color-text-primary);
    left: 2px;
    transition: left 0.2s ease;
  }

  .toggle-thumb.on {
    left: calc(44px - 20px - 2px);
  }

  .toggle-switch:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }

  .empty-state {
    font-size: 14px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-muted);
    line-height: 1.4;
  }

  .field-group {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .field-group label {
    font-size: 16px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-text-primary);
  }

  .field-group input {
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    color: var(--color-text-primary);
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 16px;
    min-height: 44px;
  }

  .field-group input:focus {
    border-color: var(--color-accent);
    outline: none;
  }

  .button-row {
    display: flex;
    gap: var(--spacing-sm);
    flex-wrap: wrap;
  }

  .primary-btn {
    background: var(--color-accent);
    color: #0f1117;
    font-weight: 600;
    border-radius: var(--radius-md);
    min-height: 44px;
    padding: 0 var(--spacing-lg);
    border: none;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 16px;
    cursor: pointer;
    transition: opacity var(--transition-fast);
  }

  .primary-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
</style>
