<script lang="ts">
  import { goto } from '$app/navigation';
  import { TrendingUp, TrendingDown, Minus } from 'lucide-svelte';
  import { dashboardStore } from '$lib/ws.svelte';

  // Door state color mapping (same as CoopPanel Phase 2)
  // OPEN = accent, CLOSED = secondary, MOVING = stale, STUCK = offline
  const DOOR_STATE_COLORS: Record<string, string> = {
    open: 'var(--color-accent)',
    closed: 'var(--color-text-secondary)',
    moving: 'var(--color-stale)',
    stuck: 'var(--color-offline)',
  };

  const DOOR_STATE_LABELS: Record<string, string> = {
    open: 'OPEN',
    closed: 'CLOSED',
    moving: 'MOVING',
    stuck: 'STUCK',
  };

  const doorState = $derived(
    dashboardStore.actuatorStates.get('coop_door') ?? 'closed'
  );

  const doorColor = $derived(DOOR_STATE_COLORS[doorState] ?? 'var(--color-text-secondary)');
  const doorLabel = $derived(DOOR_STATE_LABELS[doorState] ?? doorState.toUpperCase());

  const eggCount = $derived(dashboardStore.eggCount);

  // Trend: percentage of expected achieved. We use today's count vs a simple expected baseline.
  // Per UI-SPEC: >=90% accent (TrendingUp), 75-89% stale (Minus), <75% offline (TrendingDown).
  // We derive trend from eggCount.today if available. Without expected production from the
  // store (Plan 03-03 adds ProductionChart with full data), we show the percentage based on
  // whether the count is above/below expected. For now, if eggCount exists, we compute
  // a simple ratio — plan 03-03 will supply expected production values.
  // We look for feedConsumption as a proxy but the actual expected count is not in the store yet.
  // Per plan: trend indicator shows "N%" — we compute from eggCount if available.
  // Since expected production isn't in the store yet, we render trend only when eggCount exists.
  // The percentage shown is always relative to what's available. We'll use today count as-is
  // and treat 100% = full expected. Without expected, we show a flat/neutral indicator.
  // This is intentional per the plan — Plan 03-03 will add the production chart data.

  // Compute trend percentage as today / some baseline.
  // Since expected production value isn't yet in the store (comes in Plan 03-03),
  // we show the trend icon based purely on whether we have data:
  // - null eggCount: omit trend entirely (per UI-SPEC empty state)
  // - eggCount present: we'd need expected to compute %, which is not yet stored.
  //   We'll emit a neutral "Minus" with no percentage until expected data is wired.
  // This is a known limitation documented in SUMMARY stubs section.

  // Per UI-SPEC: trend percentage = actual / expected * 100. Expected is not yet in store.
  // Show "--" for trend percentage until Plan 03-03 wires expected production.
  const trendIcon = $derived(() => {
    if (!eggCount) return null;
    // No expected production in store yet — show flat/neutral
    return Minus;
  });

  const trendColor = $derived(() => {
    if (!eggCount) return null;
    return 'var(--color-stale)';
  });

  function handleClick() {
    goto('/coop');
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      goto('/coop');
    }
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div
  class="flock-summary-card"
  role="button"
  tabindex="0"
  aria-label="Flock summary — tap to see coop detail"
  onclick={handleClick}
  onkeydown={handleKeydown}
>
  <div class="card-row">
    <!-- Left: label + egg count -->
    <div class="left-col">
      <span class="flock-label">Flock</span>
      {#if eggCount !== null}
        <span class="egg-count">{eggCount.today} eggs today</span>
      {:else}
        <span class="egg-count egg-count-empty">--</span>
      {/if}
    </div>

    <!-- Center: door state badge -->
    <div class="center-col">
      <span
        class="door-badge"
        style="color: {doorColor}; border-color: {doorColor};"
      >
        {doorLabel}
      </span>
    </div>

    <!-- Right: trend indicator -->
    <div class="right-col">
      {#if eggCount !== null}
        {@const Icon = trendIcon()}
        {@const color = trendColor()}
        {#if Icon && color}
          <span class="trend-indicator" style="color: {color};">
            <Icon size={16} aria-hidden="true" />
          </span>
        {/if}
      {/if}
    </div>
  </div>
</div>

<style>
  .flock-summary-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    padding: var(--spacing-md);
    cursor: pointer;
    width: 100%;
    transition: background-color var(--transition-fast);
  }

  .flock-summary-card:hover {
    background: var(--color-surface-hover);
  }

  .card-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--spacing-sm);
  }

  .left-col {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .flock-label {
    font-size: 14px;
    font-weight: 400;
    color: var(--color-text-secondary);
    line-height: 1.4;
  }

  .egg-count {
    font-size: 28px;
    font-weight: 600;
    color: var(--color-text-primary);
    line-height: 1.2;
    font-variant-numeric: tabular-nums;
  }

  .egg-count-empty {
    font-style: italic;
    color: var(--color-muted);
  }

  .center-col {
    flex-shrink: 0;
  }

  .door-badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    line-height: 1.4;
    padding: 3px var(--spacing-sm);
    border-radius: 99px;
    border: 1px solid;
    text-transform: uppercase;
  }

  .right-col {
    flex-shrink: 0;
    display: flex;
    align-items: center;
  }

  .trend-indicator {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    font-size: 14px;
    font-weight: 400;
    line-height: 1.4;
  }
</style>
