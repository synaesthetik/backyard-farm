<script lang="ts">
  import { goto } from '$app/navigation';
  import { ChevronLeft, ChevronRight } from 'lucide-svelte';

  const STEP = 3;
  const TOTAL_STEPS = 8;
  const COMPLETE_KEY = 'tutorial_completed';
  const STORAGE_KEY = 'tutorial_step';

  function markDone() {
    if (STEP >= TOTAL_STEPS) {
      localStorage.setItem(COMPLETE_KEY, 'true');
      localStorage.removeItem(STORAGE_KEY);
      goto('/tutorial/8');
    } else {
      const next = STEP + 1;
      localStorage.setItem(STORAGE_KEY, String(next));
      goto(`/tutorial/${next}`);
    }
  }
</script>

<svelte:head><title>Farm Tutorial — Step 3: Add Your First Zone</title></svelte:head>

<div class="step-card">
  <h2 class="step-heading">Add Your First Zone</h2>
  <div class="step-body">
    <p>Navigate to <a href="/settings/zones" class="step-link">Settings → Zones</a> (or use the link below). Click "Add Zone" and fill in:</p>
    <ul>
      <li>Zone name (e.g., "Tomatoes")</li>
      <li>Soil type (loam, clay, sandy)</li>
      <li>Target VWC range: 30–60% is typical for most vegetables</li>
      <li>pH target: 6.0–7.0 for most crops</li>
      <li>Irrigation zone ID: matches the relay/valve number on your hardware</li>
    </ul>
    <p><a href="/settings/zones" class="step-link">Open Zone Settings →</a></p>
  </div>
  <div class="step-actions">
    <a href="/tutorial/{STEP - 1}" class="btn-secondary">
      <ChevronLeft size={16} /> Back
    </a>
    <button class="btn-primary" onclick={markDone}>
      I did this <ChevronRight size={16} />
    </button>
  </div>
</div>

<style>
  .step-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    padding: var(--spacing-lg);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
    flex: 1;
  }
  .step-heading {
    font-size: 20px;
    font-weight: 600;
    color: var(--color-text);
    font-family: 'Inter', system-ui, sans-serif;
    margin: 0;
  }
  .step-body {
    font-size: 15px;
    line-height: 1.6;
    color: var(--color-text-secondary);
    font-family: 'Merriweather', Georgia, serif;
  }
  .step-body p { margin: 0 0 var(--spacing-sm); }
  .step-body p:last-child { margin-bottom: 0; }
  .step-body ul {
    margin: var(--spacing-sm) 0;
    padding-left: var(--spacing-lg);
  }
  .step-body li { margin-bottom: 4px; }
  .step-link {
    color: var(--color-accent);
    text-decoration: none;
  }
  .step-link:hover { text-decoration: underline; }
  .step-actions {
    display: flex;
    gap: var(--spacing-sm);
    justify-content: flex-end;
    margin-top: auto;
    padding-top: var(--spacing-md);
  }
  .btn-primary {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 10px 20px;
    background: var(--color-accent);
    color: #0f1a0f;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    font-family: 'Inter', system-ui, sans-serif;
    cursor: pointer;
    transition: opacity var(--transition-fast);
  }
  .btn-primary:hover { opacity: 0.85; }
  .btn-secondary {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 10px 16px;
    background: transparent;
    color: var(--color-text-secondary);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    font-size: 14px;
    font-family: 'Inter', system-ui, sans-serif;
    text-decoration: none;
    transition: color var(--transition-fast), border-color var(--transition-fast);
  }
  .btn-secondary:hover { color: var(--color-text); border-color: var(--color-text-secondary); }
</style>
