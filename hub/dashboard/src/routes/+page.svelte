<script lang="ts">
  import { dashboardStore } from '$lib/ws.svelte';
  import ZoneCard from '$lib/ZoneCard.svelte';
  import FlockSummaryCard from '$lib/FlockSummaryCard.svelte';
  import AIStatusCard from '$lib/AIStatusCard.svelte';
</script>

<svelte:head>
  <title>Farm — Dashboard</title>
</svelte:head>

<div class="home-layout">
  <!-- FlockSummaryCard: top on mobile, right column on desktop -->
  <div class="flock-col">
    <AIStatusCard />
    <FlockSummaryCard />
  </div>

  <!-- Zone cards: below flock on mobile, left column on desktop -->
  <div class="zones-col">
    {#if dashboardStore.zones.size === 0}
      <div class="empty-zones">
        <p class="empty-heading">No zones configured</p>
        <p class="empty-body">Add a zone in settings to get started.</p>
      </div>
    {:else}
      <div class="zone-grid">
        {#each [...dashboardStore.zones.values()] as zone (zone.zone_id)}
          <ZoneCard
            {zone}
            healthScore={dashboardStore.zoneHealthScores.get(zone.zone_id)?.score}
            compact={true}
          />
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  /* Mobile: single column, flock summary first */
  .home-layout {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .flock-col {
    order: 1;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .zones-col {
    order: 2;
  }

  /* Desktop (>= 640px): 2-column grid, zones left (wider), status right */
  @media (min-width: 640px) {
    .home-layout {
      display: grid;
      grid-template-columns: 3fr 2fr;
      grid-template-rows: auto;
      gap: var(--spacing-lg);
      align-items: start;
    }

    .zones-col {
      order: 1;
      grid-column: 1;
    }

    .flock-col {
      order: 2;
      grid-column: 2;
      position: sticky;
      top: 120px;
    }
  }

  .zone-grid {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
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
    color: var(--color-muted);
  }
</style>
