<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';

  const TOTAL_STEPS = 8;
  const STORAGE_KEY = 'tutorial_step';

  let { children } = $props();
  let currentStep = $state(1);

  onMount(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) currentStep = parseInt(saved, 10);
  });

  const stepFromUrl = $derived(() => {
    const match = $page.url.pathname.match(/\/tutorial\/(\d+)/);
    return match ? parseInt(match[1], 10) : currentStep;
  });
</script>

<div class="tutorial-shell">
  <div class="tutorial-progress-bar" role="progressbar"
       aria-valuenow={stepFromUrl()} aria-valuemin={1} aria-valuemax={TOTAL_STEPS}>
    <div class="tutorial-progress-fill"
         style="width: {(stepFromUrl() / TOTAL_STEPS) * 100}%"></div>
  </div>
  <div class="tutorial-step-counter">
    Step {stepFromUrl()} of {TOTAL_STEPS}
  </div>
  {@render children()}
</div>

<style>
  .tutorial-shell {
    max-width: 640px;
    margin: 0 auto;
    padding: var(--spacing-lg);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
    min-height: 100vh;
  }
  .tutorial-progress-bar {
    height: 4px;
    background: var(--color-border);
    border-radius: 2px;
    overflow: hidden;
  }
  .tutorial-progress-fill {
    height: 100%;
    background: var(--color-accent);
    border-radius: 2px;
    transition: width var(--transition-fast);
  }
  .tutorial-step-counter {
    font-size: 12px;
    color: var(--color-muted);
    font-family: 'Inter', system-ui, sans-serif;
    text-align: right;
  }
</style>
