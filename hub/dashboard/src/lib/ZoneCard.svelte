<script lang="ts">
  import { goto } from '$app/navigation';
  import { Droplets, FlaskConical, Thermometer, AlertTriangle } from 'lucide-svelte';
  import SensorValue from './SensorValue.svelte';
  import HealthBadge from './HealthBadge.svelte';
  import { isStale, formatElapsed } from './ws.svelte';
  import type { ZoneState, HealthScore } from './types';

  interface Props {
    zone: ZoneState;
    healthScore?: HealthScore;
  }

  let { zone, healthScore }: Props = $props();

  const MAX_ZONE_NAME_CHARS = 20;

  const latestReceivedAt = $derived.by((): string | null => {
    const timestamps = [zone.moisture, zone.ph, zone.temperature]
      .filter((r) => r !== null)
      .map((r) => r!.received_at);
    if (timestamps.length === 0) return null;
    return timestamps.sort().at(-1) ?? null;
  });

  const zoneIsStale = $derived.by((): boolean => {
    const ts = latestReceivedAt;
    if (!ts) return false;
    return isStale(ts);
  });

  const zoneIsStuck = $derived.by((): boolean => {
    return [zone.moisture, zone.ph, zone.temperature].some((r) => r?.stuck === true);
  });

  function truncateName(name: string): string {
    if (name.length > MAX_ZONE_NAME_CHARS) {
      return name.slice(0, MAX_ZONE_NAME_CHARS) + '\u2026';
    }
    return name;
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      goto(`/zones/${zone.zone_id}`);
    }
  }
</script>

<section
  class="zone-card"
  class:stale={zoneIsStale}
  aria-label={zone.zone_id}
  role="button"
  tabindex="0"
  onclick={() => goto(`/zones/${zone.zone_id}`)}
  onkeydown={handleKeydown}
>
  <div class="zone-header">
    <h2 class="zone-name">{truncateName(zone.zone_id)}</h2>
    {#if healthScore !== undefined}
      <HealthBadge score={healthScore} />
    {/if}
  </div>

  <div class="freshness">
    {#if latestReceivedAt === null}
      <span class="freshness-no-data">No data received</span>
    {:else if zoneIsStale}
      <AlertTriangle size={14} color="#f59e0b" />
      <span class="freshness-stale">STALE — last updated {formatElapsed(latestReceivedAt)}</span>
    {:else}
      <span class="freshness-current">Updated {formatElapsed(latestReceivedAt)}</span>
    {/if}
  </div>

  <div class="sensors" class:dimmed={zoneIsStale}>
    <SensorValue
      icon={Droplets}
      label="Moisture"
      value={zone.moisture?.value ?? null}
      unit="%"
      quality={zone.moisture?.quality ?? null}
    />
    <SensorValue
      icon={FlaskConical}
      label="pH"
      value={zone.ph?.value ?? null}
      unit=""
      quality={zone.ph?.quality ?? null}
    />
    <SensorValue
      icon={Thermometer}
      label="Temp"
      value={zone.temperature?.value ?? null}
      unit="°C"
      quality={zone.temperature?.quality ?? null}
    />
  </div>

  {#if zoneIsStuck}
    <div class="stuck-indicator">
      <AlertTriangle size={14} color="#f97316" />
      <span>Stuck sensor detected</span>
    </div>
  {/if}
</section>

<style>
  .zone-card {
    background-color: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--spacing-md);
    cursor: pointer;
    box-shadow: var(--shadow-card);
    transition: transform var(--transition-fast), box-shadow var(--transition-base), border-color var(--transition-base);
  }

  .zone-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-card-hover);
    border-color: var(--color-accent-dim);
  }

  .zone-card:active {
    transform: translateY(0);
  }

  .zone-card.stale {
    border-color: var(--color-stale);
  }

  .zone-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-xs);
  }

  .zone-name {
    font-size: 28px;
    font-weight: 600;
    line-height: 1.2;
    color: var(--color-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .freshness {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    font-size: 14px;
    font-weight: 400;
    line-height: 1.4;
    margin-bottom: var(--spacing-md);
    min-height: 20px;
  }

  .freshness-no-data {
    color: var(--color-muted);
  }

  .freshness-stale {
    color: #f59e0b;
  }

  .freshness-current {
    color: var(--color-text-secondary);
  }

  .sensors {
    display: flex;
    flex-direction: column;
  }

  .sensors.dimmed :global(.sensor-value) {
    opacity: 0.5;
  }

  .stuck-indicator {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    margin-top: var(--spacing-sm);
    padding-top: var(--spacing-sm);
    border-top: 1px solid var(--color-border);
    font-size: 14px;
    font-weight: 400;
    color: #f97316;
  }
</style>
