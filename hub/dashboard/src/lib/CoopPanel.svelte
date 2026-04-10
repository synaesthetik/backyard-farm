<script lang="ts">
  import { DoorOpen, DoorClosed, RefreshCw, Settings } from 'lucide-svelte';
  import CommandButton from '$lib/CommandButton.svelte';
  import HenPresentIndicator from '$lib/HenPresentIndicator.svelte';
  import ProductionChart from '$lib/ProductionChart.svelte';
  import FeedSparkline from '$lib/FeedSparkline.svelte';
  import { dashboardStore } from '$lib/ws.svelte';
  import { goto } from '$app/navigation';

  const doorState = $derived(dashboardStore.actuatorStates.get('coop_door') ?? 'closed');

  const doorColorMap: Record<string, string> = {
    open: 'var(--color-accent)',
    closed: 'var(--color-text-secondary)',
    moving: 'var(--color-stale)',
    stuck: 'var(--color-offline)',
  };

  const doorLabelMap: Record<string, string> = {
    open: 'OPEN',
    closed: 'CLOSED',
    moving: 'MOVING',
    stuck: 'STUCK',
  };

  const doorColor = $derived(doorColorMap[doorState] ?? 'var(--color-text-secondary)');
  const doorLabel = $derived(doorLabelMap[doorState] ?? doorState.toUpperCase());
  const isMoving = $derived(doorState === 'moving');

  let doorLoading = $state<'open' | 'close' | null>(null);

  async function sendDoorCommand(action: 'open' | 'close') {
    doorLoading = action;
    try {
      const res = await fetch('/api/actuators/coop-door', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      if (!res.ok) {
        window.dispatchEvent(
          new CustomEvent('farm:toast', {
            detail: { message: 'Command failed \u2014 tap to retry' },
          })
        );
      }
    } catch {
      window.dispatchEvent(
        new CustomEvent('farm:toast', {
          detail: { message: 'Command failed \u2014 tap to retry' },
        })
      );
    } finally {
      doorLoading = null;
    }
  }

  function formatScheduleTime(isoString: string): string {
    return new Date(isoString).toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }

  const feedLevel = $derived(dashboardStore.feedLevel);
  const waterLevel = $derived(dashboardStore.waterLevel);
  const coopSchedule = $derived(dashboardStore.coopSchedule);
  const eggCount = $derived(dashboardStore.eggCount);
  const feedConsumption = $derived(dashboardStore.feedConsumption);

  let refreshing = $state(false);

  async function handleRefresh() {
    refreshing = true;
    try {
      const res = await fetch('/api/flock/refresh-eggs', { method: 'POST' });
      if (!res.ok) {
        window.dispatchEvent(
          new CustomEvent('farm:toast', {
            detail: { message: 'Refresh failed \u2014 tap to retry' },
          })
        );
      }
      // State update handled via WebSocket delta
    } catch {
      window.dispatchEvent(
        new CustomEvent('farm:toast', {
          detail: { message: 'Refresh failed \u2014 tap to retry' },
        })
      );
    } finally {
      refreshing = false;
    }
  }
</script>

<div class="coop-panel">
  <!-- Egg count section -->
  <section class="egg-section">
    <div class="egg-section-header">
      <div class="egg-count-col">
        <h2 class="section-heading">Eggs Today</h2>
        <div class="egg-count-row">
          <span class="egg-count" class:egg-count-null={eggCount === null}>
            {#if eggCount !== null}
              {eggCount.today} eggs
            {:else}
              <span class="no-data-dash">--</span>
            {/if}
          </span>
        </div>
        {#if eggCount?.hen_present}
          <HenPresentIndicator />
        {/if}
      </div>
      <div class="egg-actions">
        <button
          class="refresh-btn"
          class:refreshing
          disabled={refreshing}
          aria-disabled={refreshing}
          aria-busy={refreshing}
          aria-label="Refresh egg count"
          onclick={handleRefresh}
        >
          <span class="refresh-icon" class:spin={refreshing} aria-hidden="true">
            <RefreshCw size={16} />
          </span>
          Refresh
        </button>
        <button
          class="settings-btn"
          aria-label="Flock settings"
          onclick={() => goto('/coop/settings')}
        >
          <Settings size={24} />
        </button>
      </div>
    </div>
  </section>

  <!-- Production chart section -->
  <section class="production-section">
    <h2 class="section-heading">Egg Production — 30 Days</h2>
    <ProductionChart />
  </section>

  <!-- Door status hero -->
  <section class="door-hero" class:door-open={doorState === 'open'} class:door-stuck={doorState === 'stuck'} class:door-moving={doorState === 'moving'}>
    <div class="door-icon" style="color: {doorColor}">
      {#if doorState === 'open' || doorState === 'moving'}
        <DoorOpen size={48} />
      {:else}
        <DoorClosed size={48} />
      {/if}
    </div>
    <span class="door-status-label" aria-live="polite" style="color: {doorColor}">{doorLabel}</span>
    {#if coopSchedule}
      <span class="door-schedule-hint">
        {doorState === 'open' ? `Closes at ${formatScheduleTime(coopSchedule.close_at)}` : `Opens at ${formatScheduleTime(coopSchedule.open_at)}`}
      </span>
    {/if}
    <div class="door-controls">
      <CommandButton
        label="Open door"
        loading={isMoving || doorLoading === 'open'}
        disabled={doorState === 'open' || isMoving}
        onclick={() => sendDoorCommand('open')}
      />
      <CommandButton
        label="Close door"
        loading={isMoving || doorLoading === 'close'}
        disabled={doorState === 'closed' || isMoving}
        onclick={() => sendDoorCommand('close')}
      />
    </div>
  </section>

  <!-- Feed level section -->
  <section class="level-section">
    <h2 class="section-heading">Feed</h2>
    {#if feedLevel}
      <div class="level-row">
        <div class="progress-bar">
          <div
            class="progress-fill"
            style="width: {feedLevel.percentage}%; background: {feedLevel.below_threshold ? 'var(--color-stale)' : 'var(--color-accent)'};"
          ></div>
        </div>
        <span class="level-label">{feedLevel.percentage}% full</span>
      </div>
      {#if feedConsumption}
        <div class="feed-consumption-row">
          <span class="feed-rate">~{Math.round(feedConsumption.rate_grams_per_day)}g/day</span>
          <FeedSparkline values={feedConsumption.weekly} />
        </div>
      {/if}
    {:else}
      <p class="no-data">No data</p>
    {/if}
  </section>

  <!-- Water level section -->
  <section class="level-section">
    <h2 class="section-heading">Water</h2>
    {#if waterLevel}
      <div class="level-row">
        <div class="progress-bar">
          <div
            class="progress-fill"
            style="width: {waterLevel.percentage}%; background: {waterLevel.below_threshold ? 'var(--color-stale)' : '#60a5fa'};"
          ></div>
        </div>
        <span class="level-label">{waterLevel.percentage}% full</span>
      </div>
    {:else}
      <p class="no-data">No data</p>
    {/if}
  </section>
</div>

<style>
  .coop-panel {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
  }

  .section-heading {
    font-size: 20px;
    font-weight: 600;
    line-height: 1.2;
    margin-bottom: var(--spacing-sm);
    color: var(--color-text-primary);
  }

  /* Egg section */
  .egg-section {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--spacing-md);
    box-shadow: var(--shadow-card);
  }

  .egg-section-header {
    display: flex;
    flex-direction: row;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--spacing-sm);
  }

  .egg-count-col {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .egg-count-row {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .egg-count {
    font-size: 28px;
    font-weight: 600;
    line-height: 1.2;
    color: var(--color-text-primary);
    font-variant-numeric: tabular-nums;
  }

  .no-data-dash {
    font-size: 28px;
    font-weight: 400;
    font-style: italic;
    color: var(--color-muted);
  }

  .egg-actions {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    flex-shrink: 0;
  }

  .refresh-btn {
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-xs);
    min-height: 44px;
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text-primary);
    font-family: inherit;
    font-size: 16px;
    font-weight: 400;
    line-height: 1.5;
    cursor: pointer;
    transition: opacity var(--transition-fast), background-color var(--transition-fast);
  }

  .refresh-btn:hover:not(:disabled) {
    background: var(--color-surface-hover);
  }

  .refresh-btn:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }

  .refresh-icon {
    display: inline-flex;
    align-items: center;
  }

  .refresh-icon.spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .settings-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 44px;
    min-width: 44px;
    padding: var(--spacing-sm);
    background: transparent;
    border: none;
    color: var(--color-text-secondary);
    cursor: pointer;
    border-radius: var(--radius-md);
    transition: color var(--transition-fast), background-color var(--transition-fast);
  }

  .settings-btn:hover {
    color: var(--color-text-primary);
    background: var(--color-surface-hover);
  }

  /* Production section */
  .production-section {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--spacing-md);
    box-shadow: var(--shadow-card);
  }

  /* Door hero */
  .door-hero {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: var(--spacing-lg) var(--spacing-md);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-card);
    gap: var(--spacing-sm);
    transition: border-color var(--transition-base), box-shadow var(--transition-base);
  }

  .door-hero.door-open {
    border-color: rgba(74, 222, 128, 0.3);
    box-shadow: var(--shadow-card), 0 0 20px rgba(74, 222, 128, 0.08);
  }

  .door-hero.door-stuck {
    border-color: rgba(239, 68, 68, 0.4);
    box-shadow: var(--shadow-card), 0 0 20px rgba(239, 68, 68, 0.1);
  }

  .door-hero.door-moving {
    border-color: rgba(245, 158, 11, 0.3);
  }

  .door-icon {
    transition: transform var(--transition-base);
  }

  .door-hero.door-moving .door-icon {
    animation: pulse 1.5s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  .door-status-label {
    font-size: 32px;
    font-weight: 700;
    letter-spacing: 0.06em;
    line-height: 1.2;
  }

  .door-schedule-hint {
    font-size: 14px;
    color: var(--color-text-secondary);
    font-style: italic;
  }

  .door-controls {
    display: flex;
    gap: var(--spacing-sm);
    margin-top: var(--spacing-sm);
  }

  /* Level section */
  .level-section {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--spacing-md);
    box-shadow: var(--shadow-card);
  }

  .level-row {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .progress-bar {
    flex: 1;
    height: 8px;
    background: var(--color-border);
    border-radius: 4px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .level-label {
    font-size: 16px;
    font-weight: 400;
    color: var(--color-text-primary);
    white-space: nowrap;
  }

  .feed-consumption-row {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: var(--spacing-sm);
    margin-top: var(--spacing-sm);
  }

  .feed-rate {
    font-size: 14px;
    font-weight: 400;
    color: var(--color-text-secondary);
    font-variant-numeric: tabular-nums;
  }

  .no-data {
    font-size: 14px;
    color: var(--color-muted);
  }
</style>
