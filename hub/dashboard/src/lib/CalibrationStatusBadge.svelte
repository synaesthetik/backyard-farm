<script lang="ts">
  let {
    days_since,
  }: {
    days_since: number | null;
  } = $props();

  type BadgeState = 'overdue' | 'due_soon' | 'current';

  const state = $derived<BadgeState>(
    days_since === null || days_since > 14
      ? 'overdue'
      : days_since >= 12
        ? 'due_soon'
        : 'current'
  );

  const label = $derived(
    state === 'overdue'
      ? 'OVERDUE'
      : state === 'due_soon'
        ? `Due in ${14 - days_since!} days`
        : `Calibrated ${days_since} days ago`
  );
</script>

<span
  class="calibration-badge"
  class:overdue={state === 'overdue'}
  class:due-soon={state === 'due_soon'}
  class:current={state === 'current'}
>
  {label}
</span>

<style>
  .calibration-badge {
    display: inline-block;
    font-size: 14px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    border-radius: 4px;
    padding: 2px var(--spacing-sm);
    line-height: 1.4;
  }

  .calibration-badge.overdue {
    background: var(--color-stale);
    color: #0f1117;
  }

  .calibration-badge.due-soon {
    background: var(--color-stale);
    color: #0f1117;
  }

  .calibration-badge.current {
    background: var(--color-border);
    color: var(--color-text-secondary);
  }
</style>
