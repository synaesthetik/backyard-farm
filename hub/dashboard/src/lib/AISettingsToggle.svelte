<script lang="ts">
  import type { AIDomain, AIMode, ModelMaturityEntry } from './types';

  let {
    domain,
    entry,
  }: {
    domain: AIDomain;
    entry: ModelMaturityEntry | null;
  } = $props();

  const DESCRIPTIONS: Record<AIDomain, string> = {
    irrigation: 'ONNX model optimizes irrigation timing based on soil moisture patterns.',
    zone_health: 'ONNX model scores zone health using learned sensor patterns.',
    flock_anomaly: 'ONNX model detects production anomalies beyond the expected-egg model.',
  };

  const LABELS: Record<AIDomain, string> = {
    irrigation: 'Irrigation Recommendations',
    zone_health: 'Zone Health Scoring',
    flock_anomaly: 'Flock Anomaly Detection',
  };

  let serverMode = $derived<AIMode>(entry?.mode ?? 'rules');
  let optimisticMode = $state<AIMode | null>(null);
  let mode = $derived<AIMode>(optimisticMode ?? serverMode);
  let isMature = $derived(entry?.gate_passed ?? false);
  let isDisabled = $derived(!isMature);

  async function toggle() {
    if (isDisabled) return;
    const newMode: AIMode = mode === 'ai' ? 'rules' : 'ai';
    const prevMode = mode;
    optimisticMode = newMode; // Optimistic update

    try {
      const res = await fetch('/api/settings/ai', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain, mode: newMode }),
      });
      if (!res.ok) throw new Error('Failed');
      const toastMsg = newMode === 'ai'
        ? `AI enabled for ${LABELS[domain].toLowerCase()}`
        : `Rules restored for ${LABELS[domain].toLowerCase()}`;
      window.dispatchEvent(new CustomEvent('farm:toast', { detail: { message: toastMsg } }));
    } catch {
      optimisticMode = prevMode; // Revert on failure
      window.dispatchEvent(new CustomEvent('farm:toast', {
        detail: { message: 'Settings update failed — check connection' },
      }));
    }
  }
</script>

<div class="toggle-row" class:disabled={isDisabled}>
  <div class="toggle-info">
    <span class="toggle-label">{LABELS[domain]}</span>
    <span class="toggle-description">{DESCRIPTIONS[domain]}</span>
  </div>

  <button
    class="toggle-switch"
    role="switch"
    aria-checked={mode === 'ai'}
    aria-disabled={isDisabled}
    aria-label="Use AI for {LABELS[domain]}"
    title={isDisabled ? 'Model not yet mature' : undefined}
    style={isDisabled ? 'opacity: 0.5; cursor: not-allowed;' : ''}
    onclick={toggle}
    type="button"
  >
    <span class="toggle-thumb" class:on={mode === 'ai'}></span>
  </button>
</div>

<style>
  .toggle-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--spacing-md);
    min-height: 44px;
  }

  .toggle-info {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    flex: 1;
  }

  .toggle-label {
    font-size: 16px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-text-primary);
    line-height: 1.5;
  }

  .toggle-description {
    font-size: 14px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-muted);
    line-height: 1.4;
  }

  .toggle-switch {
    position: relative;
    width: 44px;
    height: 24px;
    border-radius: 12px;
    border: none;
    background: var(--color-border);
    cursor: pointer;
    flex-shrink: 0;
    padding: 0;
    min-height: 44px;
    min-width: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background var(--transition-base);
  }

  .toggle-switch[aria-checked="true"] {
    background: var(--color-accent);
  }

  .toggle-thumb {
    position: absolute;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: var(--color-text-primary);
    left: 2px;
    transition: left 0.2s ease;
  }

  .toggle-thumb.on {
    left: calc(44px - 20px - 2px);
  }

  .toggle-switch:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }
</style>
