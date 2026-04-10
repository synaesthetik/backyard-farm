<script lang="ts">
  import { page } from '$app/stores';
  import { dashboardStore } from '$lib/ws.svelte';
  import SensorValue from '$lib/SensorValue.svelte';
  import HealthBadge from '$lib/HealthBadge.svelte';
  import CommandButton from '$lib/CommandButton.svelte';
  import SensorChart from '$lib/SensorChart.svelte';
  import { Droplets, FlaskConical, Thermometer } from 'lucide-svelte';
  import type { HealthScore } from '$lib/types';

  const zoneId = $derived($page.params.id);
  const zone = $derived(dashboardStore.zones.get(zoneId));
  const healthData = $derived(dashboardStore.zoneHealthScores.get(zoneId));
  const healthScore = $derived<HealthScore>(healthData?.score ?? 'green');
  const contributingSensors = $derived(healthData?.contributing_sensors ?? []);
  const irrigationState = $derived(
    dashboardStore.actuatorStates.get(`irrigation:${zoneId}`) ?? 'closed'
  );

  let irrigateLoading = $state(false);
  let chartDays = $state(7);

  async function sendIrrigationCommand(action: 'open' | 'close') {
    irrigateLoading = true;
    try {
      const res = await fetch('/api/actuators/irrigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zone_id: zoneId, action }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const msg = data.detail || 'Command failed \u2014 tap to retry';
        window.dispatchEvent(new CustomEvent('farm:toast', { detail: { message: msg } }));
      }
    } catch {
      window.dispatchEvent(new CustomEvent('farm:toast', {
        detail: { message: 'Command failed \u2014 tap to retry' },
      }));
    } finally {
      irrigateLoading = false;
    }
  }
</script>

<h2 class="page-heading">{zoneId}</h2>

{#if zone}
  <section class="irrigation-section">
    <div class="irrigation-status">
      <span class="status-label" class:irrigating={irrigationState === 'open'}>
        {irrigationState === 'open' ? 'Irrigating' : irrigationState === 'moving' ? 'Moving' : 'Closed'}
      </span>
      {#if healthData}
        <HealthBadge score={healthScore} />
      {/if}
    </div>
    {#if contributingSensors.length > 0}
      <p class="contributing">Affected: {contributingSensors.join(', ')}</p>
    {/if}
    <div class="irrigation-controls">
      <CommandButton
        label="Open valve"
        loading={irrigateLoading && irrigationState !== 'open'}
        disabled={irrigationState === 'open' || irrigationState === 'moving'}
        onclick={() => sendIrrigationCommand('open')}
      />
      <CommandButton
        label="Close valve"
        loading={irrigateLoading && irrigationState === 'open'}
        disabled={irrigationState === 'closed' || irrigationState === 'moving'}
        onclick={() => sendIrrigationCommand('close')}
      />
    </div>
  </section>

  <section class="sensors-section">
    {#if zone.moisture}
      <SensorValue icon={Droplets} label="Moisture" value={zone.moisture.value} unit="% VWC" quality={zone.moisture.quality} />
    {/if}
    {#if zone.ph}
      <SensorValue icon={FlaskConical} label="pH" value={zone.ph.value} unit="" quality={zone.ph.quality} />
    {/if}
    {#if zone.temperature}
      <SensorValue icon={Thermometer} label="Temperature" value={zone.temperature.value} unit="°C" quality={zone.temperature.quality} />
    {/if}
  </section>

  <section class="charts-section">
    <h3 class="section-heading">Sensor History</h3>
    <div class="range-toggle">
      <button class="range-btn" class:active={chartDays === 7} onclick={() => chartDays = 7}>7 days</button>
      <button class="range-btn" class:active={chartDays === 30} onclick={() => chartDays = 30}>30 days</button>
    </div>
    <div class="chart-stack">
      <SensorChart zoneId={zoneId} sensorType="moisture" bind:days={chartDays} />
      <SensorChart zoneId={zoneId} sensorType="ph" bind:days={chartDays} />
      <SensorChart zoneId={zoneId} sensorType="temperature" bind:days={chartDays} />
    </div>
  </section>
{:else}
  <p class="empty">Zone not found.</p>
{/if}

<style>
  .page-heading {
    font-size: 20px;
    font-weight: 600;
    line-height: 1.2;
    margin-bottom: var(--spacing-lg);
  }
  .irrigation-section {
    margin-bottom: var(--spacing-lg);
  }
  .irrigation-status {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-sm);
  }
  .status-label {
    font-size: 16px;
    font-weight: 400;
    color: var(--color-text-secondary);
  }
  .status-label.irrigating {
    color: var(--color-accent);
  }
  .contributing {
    font-size: 14px;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
  }
  .irrigation-controls {
    display: flex;
    gap: var(--spacing-sm);
  }
  .sensors-section {
    margin-bottom: var(--spacing-lg);
  }
  .charts-section {
    margin-bottom: var(--spacing-lg);
  }
  .section-heading {
    font-size: 20px;
    font-weight: 600;
    line-height: 1.2;
    margin-bottom: var(--spacing-md);
  }
  .range-toggle {
    display: flex;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
  }
  .range-btn {
    background: none;
    border: none;
    font-family: inherit;
    font-size: 14px;
    font-weight: 400;
    color: var(--color-muted);
    cursor: pointer;
    padding: var(--spacing-xs) var(--spacing-sm);
    border-bottom: 2px solid transparent;
  }
  .range-btn.active {
    color: var(--color-accent);
    border-bottom-color: var(--color-accent);
  }
  .chart-stack {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
  }
  .empty {
    color: var(--color-muted);
    font-size: 16px;
  }
</style>
