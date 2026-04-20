<script lang="ts">
  import { goto } from '$app/navigation';
  import { ChevronRight } from 'lucide-svelte';

  const STEP = 1;
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

<svelte:head><title>Farm Tutorial — Step 1: Welcome</title></svelte:head>

<div class="step-card">
  <h2 class="step-heading">Welcome to Backyard Farm</h2>
  <div class="step-body">
    <p>This tutorial walks you through setting up and operating your farm platform — from first boot to approving your first AI recommendation. You will need your hardware assembled and your Raspberry Pi nodes powered on.</p>
    <p>Each step tells you exactly what to do and links to the relevant dashboard screen. Press "I did this" to advance. You can come back any time — your progress is saved.</p>
  </div>
  <div class="step-actions">
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
</style>
