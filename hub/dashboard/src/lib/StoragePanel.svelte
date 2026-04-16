<script lang="ts">
  import type { StorageStats } from './types';

  let {
    stats,
    onpurge,
  }: {
    stats: StorageStats;
    onpurge: () => Promise<void>;
  } = $props();

  let showConfirm = $state(false);
  let purgeLoading = $state(false);

  async function handlePurge() {
    purgeLoading = true;
    try {
      await onpurge();
      showConfirm = false;
      window.dispatchEvent(new CustomEvent('farm:toast', {
        detail: { message: 'Purge complete \u2014 storage reclaimed' },
      }));
    } catch {
      window.dispatchEvent(new CustomEvent('farm:toast', {
        detail: { message: 'Purge failed \u2014 check logs' },
      }));
    } finally {
      purgeLoading = false;
    }
  }
</script>

<div class="storage-panel">
  <div class="table-container">
    <table class="storage-table">
      <thead>
        <tr>
          <th class="col-name">Table</th>
          <th class="col-size">Size</th>
        </tr>
      </thead>
      <tbody>
        {#each stats.tables as row (row.tablename)}
          <tr>
            <td class="cell-name">{row.tablename}</td>
            <td class="cell-size">{row.size}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>

  <div class="retention-note">
    <p class="retention-text">Raw readings older than 90 days are automatically purged. Hourly rollups are retained for 2 years.</p>
  </div>

  <div class="purge-section">
    {#if !showConfirm}
      <button
        class="purge-btn"
        onclick={() => { showConfirm = true; }}
        type="button"
      >
        Purge Now
      </button>
    {:else}
      <div class="confirm-panel">
        <p class="confirm-text" role="alert">
          This will permanently delete all raw sensor readings older than 90 days. This cannot be undone.
        </p>
        <div class="confirm-buttons">
          <button
            class="keep-btn"
            onclick={() => { showConfirm = false; }}
            type="button"
          >
            Keep My Data
          </button>
          <button
            class="confirm-purge-btn"
            disabled={purgeLoading}
            aria-busy={purgeLoading}
            onclick={handlePurge}
            type="button"
          >
            {purgeLoading ? 'Purging...' : 'Confirm Purge'}
          </button>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .storage-panel {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
  }

  .table-container {
    overflow-x: auto;
  }

  .storage-table {
    width: 100%;
    border-collapse: collapse;
  }

  .storage-table thead th {
    font-size: 14px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-muted);
    text-align: left;
    padding: var(--spacing-xs) var(--spacing-sm);
    border-bottom: 1px solid var(--color-border);
  }

  .col-size {
    text-align: right !important;
  }

  .cell-name {
    font-size: 16px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-text-primary);
    padding: var(--spacing-sm);
  }

  .cell-size {
    font-size: 28px;
    font-weight: 600;
    font-family: 'Inter', system-ui, sans-serif;
    font-variant-numeric: tabular-nums;
    color: var(--color-text-primary);
    text-align: right;
    padding: var(--spacing-sm);
  }

  .retention-note {
    padding: var(--spacing-sm) 0;
  }

  .retention-text {
    font-size: 14px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-muted);
    line-height: 1.4;
  }

  .purge-section {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .purge-btn {
    min-height: 44px;
    padding: 0 var(--spacing-lg);
    border: 1px solid var(--color-offline);
    color: var(--color-offline);
    background: transparent;
    border-radius: var(--radius-md);
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    align-self: flex-start;
    transition: opacity var(--transition-fast);
  }

  .purge-btn:hover {
    opacity: 0.8;
  }

  .confirm-panel {
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid var(--color-offline);
    border-radius: var(--radius-md);
    padding: var(--spacing-md);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .confirm-text {
    font-size: 14px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-text-primary);
    line-height: 1.4;
  }

  .confirm-buttons {
    display: flex;
    gap: var(--spacing-sm);
    flex-wrap: wrap;
  }

  .keep-btn {
    min-height: 44px;
    padding: 0 var(--spacing-lg);
    background: transparent;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 16px;
    font-weight: 400;
    color: var(--color-text-primary);
    cursor: pointer;
    transition: opacity var(--transition-fast);
  }

  .keep-btn:hover {
    opacity: 0.8;
  }

  .confirm-purge-btn {
    min-height: 44px;
    padding: 0 var(--spacing-lg);
    background: var(--color-offline);
    color: #f1f5f9;
    border: none;
    border-radius: var(--radius-md);
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: opacity var(--transition-fast);
  }

  .confirm-purge-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
</style>
