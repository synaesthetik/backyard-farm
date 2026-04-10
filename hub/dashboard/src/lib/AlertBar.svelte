<script lang="ts">
  import { goto } from '$app/navigation';
  import { AlertTriangle } from 'lucide-svelte';
  import type { AlertEntry } from './types';

  let { alerts = [] }: { alerts: AlertEntry[] } = $props();
</script>

{#if alerts.length > 0}
<div class="alert-bar" role="alert">
  {#each alerts as alert}
    <button
      class="alert-row"
      class:p0={alert.severity === 'P0'}
      class:p1={alert.severity === 'P1'}
      aria-live={alert.severity === 'P0' ? 'assertive' : 'polite'}
      onclick={() => goto(alert.deep_link)}
      tabindex="0"
    >
      <span class="severity-bar"></span>
      <AlertTriangle size={16} />
      <span class="alert-text">{alert.message}</span>
      {#if alert.count > 1}
        <span class="count-badge">{alert.count}</span>
      {/if}
    </button>
  {/each}
</div>
{/if}

<style>
  .alert-bar {
    width: 100%;
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
  }
  .alert-row {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    min-height: 40px;
    width: 100%;
    border: none;
    background: none;
    cursor: pointer;
    text-align: left;
    font-family: inherit;
    font-size: 16px;
    font-weight: 400;
    line-height: 1.5;
    color: var(--color-text-primary);
  }
  .alert-row:not(:last-child) {
    border-bottom: 1px solid var(--color-border);
  }
  .severity-bar {
    width: 4px;
    align-self: stretch;
    border-radius: 2px;
    flex-shrink: 0;
  }
  .p0 .severity-bar { background: var(--color-offline); }
  .p0 :global(svg) { color: var(--color-offline); }
  .p1 .severity-bar { background: var(--color-stale); }
  .p1 :global(svg) { color: var(--color-stale); }
  .alert-text {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .count-badge {
    font-size: 14px;
    font-weight: 400;
    line-height: 1.4;
    padding: 2px var(--spacing-sm);
    background: var(--color-border);
    color: var(--color-text-primary);
    border-radius: 99px;
    flex-shrink: 0;
  }
</style>
