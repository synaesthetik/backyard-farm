<script>
  import { dashboardStore } from '$lib/ws.svelte';
  import RecommendationCard from '$lib/RecommendationCard.svelte';
</script>

<h2 class="page-heading">Recommendations</h2>

{#if dashboardStore.recommendations.length === 0}
  <div class="empty-state">
    <h3 class="empty-heading">No recommendations</h3>
    <p class="empty-body">Sensor thresholds are within range.</p>
  </div>
{:else}
  <div class="rec-list">
    {#each dashboardStore.recommendations as rec (rec.recommendation_id)}
      <RecommendationCard recommendation={rec} />
    {/each}
  </div>
{/if}

<style>
  .page-heading {
    font-size: 20px;
    font-weight: 600;
    line-height: 1.2;
    margin-bottom: var(--spacing-lg);
  }
  .empty-state {
    text-align: center;
    padding: var(--spacing-xl) 0;
  }
  .empty-heading {
    font-size: 20px;
    font-weight: 600;
    line-height: 1.2;
    margin-bottom: var(--spacing-sm);
  }
  .empty-body {
    font-size: 16px;
    font-weight: 400;
    color: var(--color-muted);
  }
  .rec-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }
</style>
