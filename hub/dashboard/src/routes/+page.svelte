<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { dashboardStore } from '$lib/ws.svelte';
  import ZoneCard from '$lib/ZoneCard.svelte';
  import SystemHealthPanel from '$lib/SystemHealthPanel.svelte';

  onMount(() => dashboardStore.connect());
  onDestroy(() => dashboardStore.disconnect());

  const statusLabel: Record<string, string> = {
    connected: 'Dashboard connected',
    reconnecting: 'Reconnecting to dashboard',
    disconnected: 'Dashboard disconnected',
  };

  const statusColor: Record<string, string> = {
    connected: '#4ade80',
    reconnecting: '#f59e0b',
    disconnected: '#ef4444',
  };
</script>

<svelte:head>
  <title>Farm Dashboard</title>
</svelte:head>

<header class="site-header">
  <span class="header-title">Farm Dashboard</span>
  <span
    class="connection-dot"
    role="status"
    aria-label={statusLabel[dashboardStore.connectionStatus]}
    style:background-color={statusColor[dashboardStore.connectionStatus]}
  ></span>
</header>

<main class="page-content">
  <section class="zones-section" aria-live="polite">
    <h2 class="section-heading">Garden Zones</h2>

    {#if dashboardStore.zones.size === 0}
      <div class="empty-zones">
        <p class="empty-heading">No zones configured</p>
        <p class="empty-body">Add zones to start receiving sensor data.</p>
      </div>
    {:else}
      <div class="zone-grid">
        {#each [...dashboardStore.zones.values()] as zone (zone.zone_id)}
          <section aria-label={zone.zone_id}>
            <ZoneCard {zone} />
          </section>
        {/each}
      </div>
    {/if}
  </section>

  <div class="section-gap"></div>

  <SystemHealthPanel nodes={dashboardStore.nodes} />
</main>

<style>
  .site-header {
    position: sticky;
    top: 0;
    z-index: 10;
    height: 48px;
    background-color: var(--color-surface);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 var(--spacing-md);
  }

  .header-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--color-text-primary);
  }

  .connection-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .page-content {
    padding: var(--spacing-md);
    padding-bottom: max(var(--spacing-md), env(safe-area-inset-bottom));
  }

  .section-heading {
    font-size: 20px;
    font-weight: 600;
    line-height: 1.2;
    color: var(--color-text-primary);
    margin-bottom: var(--spacing-md);
  }

  .zone-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--spacing-lg);
  }

  @media (min-width: 640px) {
    .zone-grid {
      grid-template-columns: 1fr 1fr;
    }
  }

  .empty-zones {
    padding: var(--spacing-lg) 0;
  }

  .empty-heading {
    font-size: 20px;
    font-weight: 600;
    color: var(--color-text-primary);
    margin-bottom: var(--spacing-sm);
  }

  .empty-body {
    font-size: 16px;
    font-weight: 400;
    color: var(--color-text-secondary);
  }

  .section-gap {
    height: var(--spacing-2xl);
  }
</style>
