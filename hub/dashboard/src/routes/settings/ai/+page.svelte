<script lang="ts">
  import { dashboardStore } from '$lib/ws.svelte';
  import AISettingsToggle from '$lib/AISettingsToggle.svelte';
  import type { AIDomain } from '$lib/types';

  const DOMAINS: AIDomain[] = ['irrigation', 'zone_health', 'flock_anomaly'];

  function getEntry(domain: AIDomain) {
    return dashboardStore.modelMaturity?.find(e => e.domain === domain) ?? null;
  }
</script>

<svelte:head>
  <title>Farm — AI Settings</title>
</svelte:head>

<div class="settings-page">
  <h2 class="settings-heading">AI Engine Settings</h2>
  <div class="settings-list">
    {#each DOMAINS as domain}
      <AISettingsToggle {domain} entry={getEntry(domain)} />
    {/each}
  </div>
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

  .settings-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
  }
</style>
