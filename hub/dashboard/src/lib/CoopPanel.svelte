<script lang="ts">
  import { DoorOpen, DoorClosed } from 'lucide-svelte';
  import CommandButton from '$lib/CommandButton.svelte';
  import { dashboardStore } from '$lib/ws.svelte';

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
</script>

<div class="coop-panel">
  <!-- Door status section -->
  <section class="door-section">
    <h2 class="section-heading">Coop Door</h2>
    <div class="door-state" aria-live="polite" style="color: {doorColor}">
      {#if doorState === 'open' || doorState === 'moving'}
        <DoorOpen size={24} />
      {:else}
        <DoorClosed size={24} />
      {/if}
      <span class="door-label">{doorLabel}</span>
    </div>
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

  <!-- Schedule display -->
  {#if coopSchedule}
    <section class="schedule-section">
      <p class="schedule-label">Today's schedule</p>
      <p class="schedule-time">Opens at {formatScheduleTime(coopSchedule.open_at)}</p>
      <p class="schedule-time">Closes at {formatScheduleTime(coopSchedule.close_at)}</p>
    </section>
  {/if}

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

  /* Door section */
  .door-state {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-sm);
  }

  .door-label {
    font-size: 16px;
    font-weight: 400;
    line-height: 1.5;
  }

  .door-controls {
    display: flex;
    gap: var(--spacing-sm);
  }

  /* Schedule section */
  .schedule-label {
    font-size: 14px;
    font-weight: 400;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-xs);
  }

  .schedule-time {
    font-size: 14px;
    font-weight: 400;
    color: var(--color-text-secondary);
    line-height: 1.4;
  }

  /* Level section */
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

  .no-data {
    font-size: 14px;
    color: var(--color-muted);
  }
</style>
