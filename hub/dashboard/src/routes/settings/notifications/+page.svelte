<script lang="ts">
  import { onMount } from 'svelte';
  import NtfySettingsForm from '$lib/NtfySettingsForm.svelte';
  import type { NtfySettings } from '$lib/types';

  let ntfySettings = $state<NtfySettings | null>(null);
  let loading = $state(true);

  async function loadSettings() {
    try {
      const res = await fetch('/api/settings/notifications');
      if (res.ok) {
        ntfySettings = await res.json();
      }
    } finally {
      loading = false;
    }
  }

  async function handleSave(updated: NtfySettings) {
    const res = await fetch('/api/settings/notifications', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updated),
    });
    if (!res.ok) throw new Error('Save failed');
    ntfySettings = updated;
  }

  async function handleTest(): Promise<boolean> {
    const res = await fetch('/api/settings/notifications/test', {
      method: 'POST',
    });
    return res.ok;
  }

  onMount(() => {
    loadSettings();
  });
</script>

<svelte:head>
  <title>Farm — Push Notifications</title>
</svelte:head>

<div class="settings-page">
  <h2 class="settings-heading">Push Notifications</h2>

  {#if loading}
    <p class="loading-text">Loading notification settings...</p>
  {:else if ntfySettings}
    <NtfySettingsForm settings={ntfySettings} onsave={handleSave} ontest={handleTest} />
  {:else}
    <p class="empty">Unable to load notification settings — check connection.</p>
  {/if}
</div>

<style>
  .settings-page {
    padding: var(--spacing-md);
  }

  .settings-heading {
    font-size: 20px;
    font-weight: 600;
    font-family: 'Merriweather', Georgia, serif;
    color: var(--color-text-primary);
    line-height: 1.2;
    margin-bottom: var(--spacing-lg);
  }

  .loading-text,
  .empty {
    font-size: 16px;
    color: var(--color-muted);
    line-height: 1.5;
  }
</style>
