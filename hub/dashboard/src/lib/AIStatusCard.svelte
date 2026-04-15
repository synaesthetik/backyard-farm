<script lang="ts">
  import { dashboardStore } from './ws.svelte';
  import DomainMaturityRow from './DomainMaturityRow.svelte';

  let entries = $derived(dashboardStore.modelMaturity ?? []);
  let allMature = $derived(entries.length > 0 && entries.every(e => e.gate_passed));
  let anyImmature = $derived(entries.some(e => !e.gate_passed));
</script>

<div class="ai-status-card">
  <div class="card-header">
    <h2 class="card-heading">AI Engine</h2>
    {#if allMature}
      <span class="all-mature-badge">All Active</span>
    {/if}
  </div>

  {#if dashboardStore.modelMaturity === null}
    <!-- Loading skeleton shimmer -->
    <div class="skeleton-list">
      <div class="skeleton-row"></div>
      <div class="skeleton-row"></div>
      <div class="skeleton-row"></div>
    </div>
  {:else if allMature}
    <!-- Compact summary: no progress bars -->
    <p class="compact-summary">All domains are using the AI model.</p>
  {:else}
    <!-- Full domain rows -->
    <div class="domain-list">
      {#each entries as entry (entry.domain)}
        <DomainMaturityRow {entry} />
      {/each}
    </div>

    {#if anyImmature}
      <p class="cold-start-message">The AI is still learning — rule-based recommendations are active.</p>
    {/if}
  {/if}

  <a href="/settings/ai" class="configure-link">Configure AI</a>
</div>

<style>
  .ai-status-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--spacing-md);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--spacing-sm);
  }

  .card-heading {
    font-size: 20px;
    font-weight: 600;
    line-height: 1.2;
    color: var(--color-text-primary);
  }

  .all-mature-badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    line-height: 1.4;
    padding: 3px var(--spacing-sm);
    border-radius: 99px;
    text-transform: uppercase;
    background: var(--color-accent);
    color: var(--color-bg);
  }

  .domain-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
  }

  .cold-start-message {
    font-size: 14px;
    font-weight: 400;
    font-style: italic;
    color: var(--color-muted);
    line-height: 1.4;
    font-family: 'Inter', system-ui, sans-serif;
  }

  .compact-summary {
    font-size: 14px;
    font-weight: 400;
    color: var(--color-text-secondary);
    line-height: 1.4;
    font-family: 'Inter', system-ui, sans-serif;
  }

  .configure-link {
    font-size: 14px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-accent);
    text-decoration: none;
    line-height: 1.4;
    align-self: flex-start;
  }

  .configure-link:hover {
    text-decoration: underline;
  }

  /* Skeleton shimmer loading state */
  .skeleton-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .skeleton-row {
    height: 40px;
    background: var(--color-border-subtle);
    border-radius: var(--radius-sm);
    animation: shimmer 1.5s ease-in-out infinite;
  }

  @keyframes shimmer {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 1; }
  }
</style>
