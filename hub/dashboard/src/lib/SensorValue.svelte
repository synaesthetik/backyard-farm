<script lang="ts">
  import type { Component } from 'svelte';
  import type { QualityFlag } from './types';

  interface Props {
    icon: Component;
    label: string;
    value: number | null;
    unit: string;
    quality: QualityFlag | null;
    decimals?: number;
  }

  let { icon: Icon, label, value, unit, quality, decimals = 1 }: Props = $props();

  const qualityBg: Record<QualityFlag, string> = {
    GOOD: '#4ade80',
    SUSPECT: '#f59e0b',
    BAD: '#ef4444',
  };

  const qualityText: Record<QualityFlag, string> = {
    GOOD: '#0f1117',
    SUSPECT: '#0f1117',
    BAD: '#f1f5f9',
  };

  function formatValue(v: number | null): string {
    if (v === null) return '--';
    if (unit === '°C') return `${Math.round(v)}${unit}`;
    return `${v.toFixed(decimals)}${unit}`;
  }
</script>

<div class="sensor-row">
  <div class="sensor-left">
    <Icon size={16} color="var(--color-text-secondary)" />
    <span class="sensor-label">{label}</span>
  </div>
  <div class="sensor-right">
    <span class="sensor-value" class:muted={value === null}>
      {formatValue(value)}
    </span>
    {#if quality !== null}
      <span
        class="quality-badge"
        style:background-color={qualityBg[quality]}
        style:color={qualityText[quality]}
      >
        {quality}
      </span>
    {/if}
  </div>
</div>

<style>
  .sensor-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--spacing-sm) 0;
  }

  .sensor-left {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    color: var(--color-text-secondary);
    font-size: 14px;
    font-weight: 400;
  }

  .sensor-label {
    font-size: 14px;
    font-weight: 400;
    color: var(--color-text-secondary);
  }

  .sensor-right {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .sensor-value {
    font-size: 28px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    color: var(--color-text-primary);
    line-height: 1.2;
  }

  .sensor-value.muted {
    color: var(--color-muted);
    font-style: italic;
  }

  .quality-badge {
    display: inline-block;
    font-size: 12px;
    font-weight: 400;
    padding: 2px var(--spacing-xs);
    border-radius: 4px;
    line-height: 1.4;
  }
</style>
