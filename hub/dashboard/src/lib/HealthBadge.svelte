<script lang="ts">
  import type { HealthScore } from './types';

  let { score = 'green' as HealthScore }: { score: HealthScore } = $props();

  const LABELS: Record<HealthScore, string> = {
    green: 'GOOD',
    yellow: 'WARN',
    red: 'CRIT',
  };

  const ARIA_LABELS: Record<HealthScore, string> = {
    green: 'Zone health: Good',
    yellow: 'Zone health: Warning',
    red: 'Zone health: Critical',
  };
</script>

<span
  class="health-badge"
  class:green={score === 'green'}
  class:yellow={score === 'yellow'}
  class:red={score === 'red'}
  aria-label={ARIA_LABELS[score]}
>
  {LABELS[score]}
</span>

<style>
  .health-badge {
    display: inline-block;
    font-size: 14px;
    font-weight: 400;
    line-height: 1.4;
    padding: 2px var(--spacing-xs);
    border-radius: 99px;
  }
  .green {
    background: var(--color-accent);
    color: var(--color-bg);
  }
  .yellow {
    background: var(--color-stale);
    color: var(--color-bg);
  }
  .red {
    background: var(--color-offline);
    color: var(--color-text-primary);
  }
</style>
