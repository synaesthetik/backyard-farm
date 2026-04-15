<script lang="ts">
  import type { ModelMaturityEntry } from './types';

  let { entry }: { entry: ModelMaturityEntry } = $props();

  const DOMAIN_LABELS: Record<string, string> = {
    irrigation: 'Irrigation',
    zone_health: 'Zone Health',
    flock_anomaly: 'Flock Anomaly',
  };

  let progressPct = $derived(Math.min((entry.weeks_of_data / 4) * 100, 100));
  let progressText = $derived(
    entry.gate_passed ? 'Mature' : `${entry.weeks_of_data} wk / 4 wk needed`
  );
  let approvalRate = $derived(
    entry.recommendation_count > 0
      ? Math.round((entry.approved_count / entry.recommendation_count) * 100)
      : null
  );
  let fillColor = $derived(
    !entry.gate_passed && entry.good_flag_ratio < 0.8
      ? 'var(--color-offline)'
      : entry.gate_passed
        ? 'var(--color-accent)'
        : 'var(--color-stale)'
  );
  let isBlocked = $derived(!entry.gate_passed && entry.good_flag_ratio < 0.8 && entry.weeks_of_data >= 4);
</script>

<div class="domain-row">
  <div class="row-header">
    <span class="domain-label">{DOMAIN_LABELS[entry.domain] ?? entry.domain}</span>
    <div class="badges">
      {#if isBlocked}
        <span
          class="mode-badge blocked"
          aria-label="{entry.domain} is using {entry.mode} recommendations"
        >BLOCKED</span>
      {:else}
        <span
          class="mode-badge"
          class:ai={entry.mode === 'ai'}
          class:rules={entry.mode !== 'ai'}
          aria-label="{entry.domain} is using {entry.mode} recommendations"
        >{entry.mode === 'ai' ? 'AI' : 'RULES'}</span>
      {/if}
      {#if approvalRate !== null}
        <span class="approval-rate">{approvalRate}% approved</span>
      {/if}
    </div>
  </div>

  <div
    class="progress-track"
    role="progressbar"
    aria-valuenow={entry.weeks_of_data}
    aria-valuemin="0"
    aria-valuemax="4"
    aria-label="{entry.domain} data maturity: {entry.weeks_of_data} of 4 weeks"
  >
    <div
      class="progress-fill"
      style="width: {progressPct}%; background: {fillColor};"
    ></div>
  </div>

  <div class="row-footer">
    <span class="progress-text">{progressText}</span>
    {#if isBlocked}
      <span class="blocked-message">Below quality threshold — check sensor calibration.</span>
    {/if}
  </div>
</div>

<style>
  .domain-row {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .row-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--spacing-sm);
  }

  .domain-label {
    font-size: 14px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-text-secondary);
    line-height: 1.4;
  }

  .badges {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    flex-shrink: 0;
  }

  .mode-badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    line-height: 1.4;
    padding: 3px var(--spacing-sm);
    border-radius: 99px;
    text-transform: uppercase;
  }

  .mode-badge.ai {
    background: var(--color-accent);
    color: var(--color-bg);
  }

  .mode-badge.rules {
    background: var(--color-border);
    color: var(--color-text-secondary);
  }

  .mode-badge.blocked {
    background: var(--color-offline);
    color: var(--color-text-primary);
  }

  .approval-rate {
    font-size: 14px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-muted);
    line-height: 1.4;
  }

  .progress-track {
    width: 100%;
    height: 8px;
    background: var(--color-border);
    border-radius: 4px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.6s ease;
  }

  .row-footer {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    flex-wrap: wrap;
  }

  .progress-text {
    font-size: 14px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-muted);
    line-height: 1.4;
  }

  .blocked-message {
    font-size: 14px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-offline);
    line-height: 1.4;
  }
</style>
