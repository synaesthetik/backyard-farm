<script lang="ts">
  import { dashboardStore } from '$lib/ws.svelte';
  import ZoneCard from '$lib/ZoneCard.svelte';
  import SystemHealthPanel from '$lib/SystemHealthPanel.svelte';
</script>

<svelte:head>
  <title>Farm Dashboard</title>
</svelte:head>

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
        <ZoneCard
          {zone}
          healthScore={dashboardStore.zoneHealthScores.get(zone.zone_id)?.score}
        />
      {/each}
    </div>
  {/if}
</section>

<div class="section-gap"></div>

<SystemHealthPanel nodes={dashboardStore.nodes} />

<style>
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
