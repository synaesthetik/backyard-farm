<script lang="ts">
  import { onMount } from 'svelte';
  import { Loader2 } from 'lucide-svelte';
  import { goto } from '$app/navigation';
  import { dashboardStore } from '$lib/ws.svelte';
  import type { FlockConfig } from '$lib/types';

  const BREEDS = [
    'Rhode Island Red', 'Leghorn', 'Plymouth Rock', 'Australorp',
    'Orpington', 'Sussex', 'Easter Egger', 'Silkie', 'Wyandotte', 'Brahma', 'Custom',
  ];

  let breed = $state('Rhode Island Red');
  let layRateOverride = $state<number | null>(null);
  let hatchDate = $state('');
  let flockSize = $state(6);
  let supplementalLighting = $state(false);
  let tareWeight = $state(0);
  let henWeightThreshold = $state(1500);
  let eggWeight = $state(60);
  let latitude = $state(0);
  let longitude = $state(0);
  let loading = $state(true);
  let saving = $state(false);
  let settingTare = $state(false);
  let error = $state('');
  let fieldErrors = $state<Record<string, string>>({});

  onMount(async () => {
    try {
      const res = await fetch('/api/flock/config');
      if (res.ok) {
        const config: FlockConfig = await res.json();
        breed = config.breed;
        layRateOverride = config.lay_rate_override;
        hatchDate = config.hatch_date;
        flockSize = config.flock_size;
        supplementalLighting = config.supplemental_lighting;
        tareWeight = config.tare_weight_grams;
        henWeightThreshold = config.hen_weight_threshold_grams;
        eggWeight = config.egg_weight_grams;
        latitude = config.latitude;
        longitude = config.longitude;
      } else {
        error = 'Failed to load flock configuration.';
      }
    } catch {
      error = 'Failed to load flock configuration.';
    } finally {
      loading = false;
    }
  });

  function onBreedChange() {
    if (breed !== 'Custom') {
      layRateOverride = null;
    }
    fieldErrors = { ...fieldErrors, breed: '' };
  }

  function validate(): boolean {
    const errors: Record<string, string> = {};

    if (!hatchDate) {
      errors.hatchDate = 'Hatch date is required.';
    }

    if (flockSize < 1) {
      errors.flockSize = 'Flock size must be at least 1.';
    }

    if (eggWeight <= 0) {
      errors.eggWeight = 'Egg weight must be greater than 0.';
    }

    if (henWeightThreshold <= 0) {
      errors.henWeightThreshold = 'Hen weight threshold must be greater than 0.';
    }

    if (breed === 'Custom') {
      if (layRateOverride === null || layRateOverride <= 0 || layRateOverride > 1.0) {
        errors.layRateOverride = 'Lay rate must be between 0.01 and 1.0.';
      }
    }

    fieldErrors = errors;
    return Object.keys(errors).length === 0;
  }

  async function handleSave() {
    if (!validate()) return;

    saving = true;
    error = '';

    const config: FlockConfig = {
      breed,
      lay_rate_override: breed === 'Custom' ? layRateOverride : null,
      hatch_date: hatchDate,
      flock_size: flockSize,
      supplemental_lighting: supplementalLighting,
      tare_weight_grams: tareWeight,
      hen_weight_threshold_grams: henWeightThreshold,
      egg_weight_grams: eggWeight,
      latitude,
      longitude,
    };

    try {
      const res = await fetch('/api/flock/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });

      if (res.ok) {
        goto('/coop');
      } else {
        const body = await res.json().catch(() => null);
        error = body?.detail ?? 'Failed to save flock configuration.';
      }
    } catch {
      error = 'Failed to save flock configuration.';
    } finally {
      saving = false;
    }
  }

  function handleSetFromSensor() {
    settingTare = true;
    const raw = dashboardStore.eggCount?.raw_weight_grams ?? null;
    if (raw === null) {
      window.dispatchEvent(
        new CustomEvent('farm:toast', {
          detail: { message: 'No sensor data available' },
        })
      );
    } else {
      tareWeight = raw;
    }
    settingTare = false;
  }
</script>

<div class="flock-settings">
  <h1 class="page-heading">Flock Settings</h1>

  {#if loading}
    <div class="form-skeleton" aria-busy="true" aria-label="Loading flock configuration">
      {#each Array(8) as _}
        <div class="skeleton-field">
          <div class="skeleton-label"></div>
          <div class="skeleton-input"></div>
        </div>
      {/each}
    </div>
  {:else}
    <form class="settings-form" onsubmit={(e) => { e.preventDefault(); handleSave(); }}>

      <!-- Breed -->
      <div class="field-group">
        <label for="breed" class="field-label">Breed</label>
        <select
          id="breed"
          class="field-input"
          bind:value={breed}
          onchange={onBreedChange}
          disabled={saving}
        >
          {#each BREEDS as b}
            <option value={b}>{b}</option>
          {/each}
        </select>
      </div>

      <!-- Custom lay rate (conditional) -->
      {#if breed === 'Custom'}
        <div class="field-group">
          <label for="layRateOverride" class="field-label">Lay rate (eggs/hen/day)</label>
          <input
            id="layRateOverride"
            type="number"
            class="field-input"
            class:field-error-input={fieldErrors.layRateOverride}
            step="0.01"
            min="0.01"
            max="1.0"
            bind:value={layRateOverride}
            disabled={saving}
            aria-describedby={fieldErrors.layRateOverride ? 'layRateOverride-error' : undefined}
          />
          {#if fieldErrors.layRateOverride}
            <p id="layRateOverride-error" class="field-error-msg" role="alert">{fieldErrors.layRateOverride}</p>
          {/if}
        </div>
      {/if}

      <!-- Hatch date -->
      <div class="field-group">
        <label for="hatchDate" class="field-label">Hatch date</label>
        <input
          id="hatchDate"
          type="date"
          class="field-input"
          class:field-error-input={fieldErrors.hatchDate}
          bind:value={hatchDate}
          disabled={saving}
          aria-describedby="hatchDate-hint{fieldErrors.hatchDate ? ' hatchDate-error' : ''}"
        />
        <p id="hatchDate-hint" class="field-hint">Used to calculate age factor</p>
        {#if fieldErrors.hatchDate}
          <p id="hatchDate-error" class="field-error-msg" role="alert">{fieldErrors.hatchDate}</p>
        {/if}
      </div>

      <!-- Flock size -->
      <div class="field-group">
        <label for="flockSize" class="field-label">Flock size (hens)</label>
        <input
          id="flockSize"
          type="number"
          class="field-input"
          class:field-error-input={fieldErrors.flockSize}
          min="1"
          step="1"
          bind:value={flockSize}
          disabled={saving}
          aria-describedby={fieldErrors.flockSize ? 'flockSize-error' : undefined}
        />
        {#if fieldErrors.flockSize}
          <p id="flockSize-error" class="field-error-msg" role="alert">{fieldErrors.flockSize}</p>
        {/if}
      </div>

      <!-- Supplemental lighting -->
      <div class="field-group field-group-checkbox">
        <label class="field-label checkbox-label">
          <input
            id="supplementalLighting"
            type="checkbox"
            class="field-checkbox"
            bind:checked={supplementalLighting}
            disabled={saving}
            aria-describedby="supplementalLighting-hint"
          />
          Supplemental lighting
        </label>
        <p id="supplementalLighting-hint" class="field-hint">Assumes 17h daylight (full production)</p>
      </div>

      <!-- Tare weight -->
      <div class="field-group">
        <label for="tareWeight" class="field-label">Nesting box tare (grams)</label>
        <div class="tare-row">
          <input
            id="tareWeight"
            type="number"
            class="field-input tare-input"
            min="0"
            step="1"
            bind:value={tareWeight}
            disabled={saving}
            aria-describedby="tareWeight-hint"
          />
          <button
            type="button"
            class="btn-secondary tare-btn"
            disabled={saving || settingTare}
            onclick={handleSetFromSensor}
          >
            {#if settingTare}
              <span class="tare-spinner" aria-hidden="true"><Loader2 size={14} /></span>
            {/if}
            Set from current reading
          </button>
        </div>
        <p id="tareWeight-hint" class="field-hint">Weigh the empty box and enter here</p>
      </div>

      <!-- Hen weight threshold -->
      <div class="field-group">
        <label for="henWeightThreshold" class="field-label">Hen weight threshold (grams)</label>
        <input
          id="henWeightThreshold"
          type="number"
          class="field-input"
          class:field-error-input={fieldErrors.henWeightThreshold}
          min="100"
          step="100"
          bind:value={henWeightThreshold}
          disabled={saving}
          aria-describedby="henWeightThreshold-hint{fieldErrors.henWeightThreshold ? ' henWeightThreshold-error' : ''}"
        />
        <p id="henWeightThreshold-hint" class="field-hint">Weight above which a hen is detected as present</p>
        {#if fieldErrors.henWeightThreshold}
          <p id="henWeightThreshold-error" class="field-error-msg" role="alert">{fieldErrors.henWeightThreshold}</p>
        {/if}
      </div>

      <!-- Egg weight -->
      <div class="field-group">
        <label for="eggWeight" class="field-label">Egg weight (grams)</label>
        <input
          id="eggWeight"
          type="number"
          class="field-input"
          class:field-error-input={fieldErrors.eggWeight}
          min="1"
          step="1"
          bind:value={eggWeight}
          disabled={saving}
          aria-describedby="eggWeight-hint{fieldErrors.eggWeight ? ' eggWeight-error' : ''}"
        />
        <p id="eggWeight-hint" class="field-hint">Used to estimate egg count from box weight</p>
        {#if fieldErrors.eggWeight}
          <p id="eggWeight-error" class="field-error-msg" role="alert">{fieldErrors.eggWeight}</p>
        {/if}
      </div>

      <!-- Latitude -->
      <div class="field-group">
        <label for="latitude" class="field-label">Latitude</label>
        <input
          id="latitude"
          type="number"
          class="field-input"
          step="0.0001"
          bind:value={latitude}
          disabled={saving}
          aria-describedby="latitude-hint"
        />
        <p id="latitude-hint" class="field-hint">For daylight calculation</p>
      </div>

      <!-- Longitude -->
      <div class="field-group">
        <label for="longitude" class="field-label">Longitude</label>
        <input
          id="longitude"
          type="number"
          class="field-input"
          step="0.0001"
          bind:value={longitude}
          disabled={saving}
        />
      </div>

      <!-- API error -->
      {#if error}
        <p class="api-error" role="alert">{error}</p>
      {/if}

      <!-- Save button -->
      <button
        type="submit"
        class="btn-save"
        disabled={loading || saving}
        aria-label="Save flock settings"
        aria-busy={saving}
      >
        {#if saving}
          <span class="save-spinner" aria-hidden="true"><Loader2 size={16} /></span>
        {/if}
        Save flock settings
      </button>

    </form>
  {/if}
</div>

<style>
  .flock-settings {
    max-width: 480px;
    margin: 0 auto;
    padding: var(--spacing-lg) var(--spacing-md);
  }

  .page-heading {
    font-size: 20px;
    font-weight: 600;
    line-height: 1.2;
    color: var(--color-text-primary);
    margin-bottom: var(--spacing-lg);
  }

  /* Skeleton loading */
  .form-skeleton {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .skeleton-field {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .skeleton-label {
    height: 14px;
    width: 120px;
    background: var(--color-surface);
    border-radius: var(--radius-sm);
  }

  .skeleton-input {
    height: 44px;
    background: var(--color-surface);
    border-radius: var(--radius-md);
  }

  /* Form */
  .settings-form {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .field-group {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .field-group-checkbox {
    gap: var(--spacing-xs);
  }

  .field-label {
    font-size: 14px;
    font-weight: 400;
    color: var(--color-text-secondary);
    line-height: 1.4;
  }

  .field-input {
    min-height: 44px;
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text-primary);
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 16px;
    font-weight: 400;
    line-height: 1.5;
    width: 100%;
    transition: border-color var(--transition-fast);
  }

  .field-input:focus {
    outline: none;
    border-color: var(--color-accent);
  }

  .field-input:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .field-error-input {
    border-color: var(--color-offline);
  }

  .field-hint {
    font-size: 14px;
    font-weight: 400;
    color: var(--color-muted);
    line-height: 1.4;
  }

  .field-error-msg {
    font-size: 16px;
    font-weight: 400;
    color: var(--color-offline);
    line-height: 1.5;
  }

  /* Checkbox */
  .checkbox-label {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    cursor: pointer;
    color: var(--color-text-primary);
    font-size: 16px;
    font-weight: 400;
  }

  .field-checkbox {
    width: 18px;
    height: 18px;
    accent-color: var(--color-accent);
    cursor: pointer;
    flex-shrink: 0;
  }

  /* Tare row */
  .tare-row {
    display: flex;
    gap: var(--spacing-sm);
    align-items: center;
  }

  .tare-input {
    flex: 1;
  }

  .btn-secondary {
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-xs);
    min-height: 44px;
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text-primary);
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 14px;
    font-weight: 400;
    line-height: 1.4;
    cursor: pointer;
    white-space: nowrap;
    transition: background-color var(--transition-fast);
    flex-shrink: 0;
  }

  .btn-secondary:hover:not(:disabled) {
    background: var(--color-surface-hover);
  }

  .btn-secondary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .tare-btn {
    /* inherits btn-secondary */
  }

  .tare-spinner {
    display: inline-flex;
    animation: spin 1s linear infinite;
  }

  /* API error */
  .api-error {
    font-size: 16px;
    font-weight: 400;
    color: var(--color-offline);
    line-height: 1.5;
    padding: var(--spacing-sm) var(--spacing-md);
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: var(--radius-md);
  }

  /* Save button */
  .btn-save {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-sm);
    width: 100%;
    min-height: 44px;
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-accent);
    color: var(--color-bg);
    border: none;
    border-radius: var(--radius-md);
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 16px;
    font-weight: 400;
    line-height: 1.5;
    cursor: pointer;
    transition: opacity var(--transition-fast), background-color var(--transition-fast);
    margin-top: var(--spacing-sm);
  }

  .btn-save:hover:not(:disabled) {
    background: #5ce98e;
  }

  .btn-save:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .save-spinner {
    display: inline-flex;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
</style>
