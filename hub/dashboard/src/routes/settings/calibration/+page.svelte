<script lang="ts">
  import { onMount } from 'svelte';
  import CalibrationStatusBadge from '$lib/CalibrationStatusBadge.svelte';
  import type { CalibrationEntry } from '$lib/types';

  let calibrations = $state<CalibrationEntry[]>([]);
  let loading = $state(true);
  let recordingFor = $state<string | null>(null);
  let expandedRow = $state<string | null>(null);
  let savingFor = $state<string | null>(null);

  // Edited field values per row key
  let editedOffsets = $state<Record<string, number>>({});
  let editedDryValues = $state<Record<string, number | null>>({});
  let editedWetValues = $state<Record<string, number | null>>({});
  let editedTempCoeffs = $state<Record<string, number>>({});

  function rowKey(entry: CalibrationEntry) {
    return `${entry.zone_id}:${entry.sensor_type}`;
  }

  function isOverdue(entry: CalibrationEntry) {
    return entry.days_since_calibration === null || entry.days_since_calibration > 14;
  }

  async function loadCalibrations() {
    try {
      const res = await fetch('/api/calibrations');
      if (res.ok) {
        const data: CalibrationEntry[] = await res.json();
        calibrations = data.filter(e => e.sensor_type === 'ph');
        // Initialize edit state from loaded data
        for (const entry of calibrations) {
          const key = rowKey(entry);
          if (!(key in editedOffsets)) {
            editedOffsets[key] = entry.offset_value;
            editedDryValues[key] = entry.dry_value;
            editedWetValues[key] = entry.wet_value;
            editedTempCoeffs[key] = entry.temp_coefficient;
          }
        }
      }
    } finally {
      loading = false;
    }
  }

  async function recordCalibration(entry: CalibrationEntry) {
    const key = rowKey(entry);
    recordingFor = key;
    try {
      const res = await fetch(`/api/calibrations/${entry.zone_id}/${entry.sensor_type}/record`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ offset: 0.0 }),
      });
      if (res.ok) {
        window.dispatchEvent(new CustomEvent('farm:toast', {
          detail: { message: `Calibration recorded for ${entry.zone_id} pH sensor` },
        }));
        await loadCalibrations();
      } else {
        window.dispatchEvent(new CustomEvent('farm:toast', {
          detail: { message: 'Calibration save failed \u2014 check connection' },
        }));
      }
    } catch {
      window.dispatchEvent(new CustomEvent('farm:toast', {
        detail: { message: 'Calibration save failed \u2014 check connection' },
      }));
    } finally {
      recordingFor = null;
    }
  }

  async function saveCalibration(entry: CalibrationEntry) {
    const key = rowKey(entry);
    savingFor = key;
    try {
      const body: Record<string, unknown> = {};
      if (editedOffsets[key] !== undefined) body.offset_value = editedOffsets[key];
      if (editedDryValues[key] !== undefined) body.dry_value = editedDryValues[key];
      if (editedWetValues[key] !== undefined) body.wet_value = editedWetValues[key];
      if (editedTempCoeffs[key] !== undefined) body.temp_coefficient = editedTempCoeffs[key];

      const res = await fetch(`/api/calibrations/${entry.zone_id}/${entry.sensor_type}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        window.dispatchEvent(new CustomEvent('farm:toast', {
          detail: { message: `Calibration saved for ${entry.zone_id} pH sensor` },
        }));
        await loadCalibrations();
      } else {
        window.dispatchEvent(new CustomEvent('farm:toast', {
          detail: { message: 'Calibration save failed \u2014 check connection' },
        }));
      }
    } catch {
      window.dispatchEvent(new CustomEvent('farm:toast', {
        detail: { message: 'Calibration save failed \u2014 check connection' },
      }));
    } finally {
      savingFor = null;
    }
  }

  function toggleExpand(key: string) {
    expandedRow = expandedRow === key ? null : key;
  }

  onMount(() => {
    loadCalibrations();
  });
</script>

<svelte:head>
  <title>Farm — Calibration Management</title>
</svelte:head>

<div class="settings-page">
  <h2 class="settings-heading">Calibration Management</h2>

  {#if loading}
    <p class="empty">Loading calibration data...</p>
  {:else if calibrations.length === 0}
    <p class="empty">No pH sensors configured. Add a zone with a pH sensor to begin tracking calibration.</p>
  {:else}
    <div class="calibration-list">
      {#each calibrations as entry (rowKey(entry))}
        {@const key = rowKey(entry)}
        {@const overdue = isOverdue(entry)}
        <div class="calibration-row-wrapper">
          <div class="calibration-row" role="button" tabindex="0"
            onclick={() => toggleExpand(key)}
            onkeydown={(e) => e.key === 'Enter' && toggleExpand(key)}>
            <div class="row-left">
              <span class="zone-name">{entry.zone_id}</span>
              <span class="sensor-type">pH sensor</span>
            </div>
            <div class="row-center">
              <CalibrationStatusBadge days_since={entry.days_since_calibration} />
            </div>
            <div class="row-right">
              <button
                class="record-btn"
                class:overdue
                disabled={recordingFor === key}
                aria-busy={recordingFor === key}
                onclick={(e) => { e.stopPropagation(); recordCalibration(entry); }}
              >
                {recordingFor === key ? 'Recording...' : 'Record Calibration'}
              </button>
            </div>
          </div>

          {#if expandedRow === key}
            <div class="expand-section">
              <div class="field-group">
                <label for="{key}-offset">Offset Value</label>
                <input
                  id="{key}-offset"
                  type="number"
                  step="0.01"
                  bind:value={editedOffsets[key]}
                />
              </div>
              <div class="field-group">
                <label for="{key}-dry">Dry Value</label>
                <input
                  id="{key}-dry"
                  type="number"
                  step="0.01"
                  bind:value={editedDryValues[key]}
                />
              </div>
              <div class="field-group">
                <label for="{key}-wet">Wet Value</label>
                <input
                  id="{key}-wet"
                  type="number"
                  step="0.01"
                  bind:value={editedWetValues[key]}
                />
              </div>
              <div class="field-group">
                <label for="{key}-temp">Temp Coefficient</label>
                <input
                  id="{key}-temp"
                  type="number"
                  step="0.001"
                  bind:value={editedTempCoeffs[key]}
                />
              </div>
              <button
                class="save-btn"
                disabled={savingFor === key}
                aria-busy={savingFor === key}
                onclick={(e) => { e.stopPropagation(); saveCalibration(entry); }}
              >
                {savingFor === key ? 'Saving...' : 'Save'}
              </button>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .settings-page {
    padding: var(--spacing-md);
  }

  .settings-heading {
    font-size: 20px;
    font-weight: 600;
    font-family: 'Merriweather', Georgia, serif;
    color: var(--color-text-primary);
    line-height: 1.2;
    margin-bottom: var(--spacing-lg);
  }

  .empty {
    font-size: 16px;
    color: var(--color-muted);
    line-height: 1.5;
  }

  .calibration-list {
    display: flex;
    flex-direction: column;
  }

  .calibration-row-wrapper {
    border-bottom: 1px solid var(--color-border);
  }

  .calibration-row {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    min-height: 44px;
    padding: var(--spacing-sm) 0;
    cursor: pointer;
    user-select: none;
  }

  .calibration-row:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }

  .row-left {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    flex: 1;
  }

  .zone-name {
    font-size: 16px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-text-primary);
  }

  .sensor-type {
    font-size: 14px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-muted);
  }

  .row-center {
    display: flex;
    align-items: center;
  }

  .row-right {
    display: flex;
    align-items: center;
  }

  .record-btn {
    min-height: 44px;
    padding: 0 var(--spacing-md);
    border-radius: var(--radius-md);
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    border: 1px solid var(--color-accent);
    color: var(--color-accent);
    background: transparent;
    transition: opacity var(--transition-fast);
    white-space: nowrap;
  }

  .record-btn.overdue {
    background: var(--color-accent);
    color: #0f1117;
  }

  .record-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .expand-section {
    padding: var(--spacing-sm) 0 var(--spacing-md);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .field-group {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .field-group label {
    font-size: 16px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-text-primary);
  }

  .field-group input {
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    color: var(--color-text-primary);
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 16px;
    min-height: 44px;
  }

  .field-group input:focus {
    border-color: var(--color-accent);
    outline: none;
  }

  .save-btn {
    min-height: 44px;
    padding: 0 var(--spacing-lg);
    border-radius: var(--radius-md);
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    background: var(--color-accent);
    color: #0f1117;
    border: none;
    align-self: flex-start;
    transition: opacity var(--transition-fast);
  }

  .save-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
</style>
