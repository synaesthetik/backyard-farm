<script lang="ts">
  import { onMount } from 'svelte';
  import StoragePanel from '$lib/StoragePanel.svelte';
  import type { StorageStats } from '$lib/types';

  let storageStats = $state<StorageStats | null>(null);
  let loading = $state(true);

  async function loadStats() {
    try {
      const res = await fetch('/api/storage/stats');
      if (res.ok) {
        storageStats = await res.json();
      }
    } finally {
      loading = false;
    }
  }

  async function handlePurge() {
    const res = await fetch('/api/storage/purge', {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Purge failed');
    await loadStats();
  }

  onMount(() => {
    loadStats();
  });
</script>

<svelte:head>
  <title>Farm — Storage &amp; Retention</title>
</svelte:head>

<div class="settings-page">
  <h2 class="settings-heading">Storage &amp; Retention</h2>

  {#if loading}
    <p class="loading-text">Loading storage data...</p>
  {:else if storageStats}
    <StoragePanel stats={storageStats} onpurge={handlePurge} />
  {:else}
    <p class="empty">Storage data unavailable \u2014 reconnect to refresh.</p>
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
