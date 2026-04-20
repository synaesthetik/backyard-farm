<script lang="ts">
  import { goto } from '$app/navigation';
  import { ChevronLeft, CheckCircle } from 'lucide-svelte';

  const STEP = 8;
  const TOTAL_STEPS = 8;
  const COMPLETE_KEY = 'tutorial_completed';
  const STORAGE_KEY = 'tutorial_step';

  function markDone() {
    localStorage.setItem(COMPLETE_KEY, 'true');
    localStorage.removeItem(STORAGE_KEY);
    goto('/tutorial/8');
  }

  function restartTutorial() {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(COMPLETE_KEY);
    goto('/tutorial/1');
  }
</script>

<svelte:head><title>Farm Tutorial — Step 8: You're All Set</title></svelte:head>

<div class="step-card">
  <h2 class="step-heading">You're All Set</h2>
  <div class="step-body">
    <p>Your farm platform is running. Here's what to check each morning:</p>
    <ul>
      <li><a href="/" class="step-link">Home tab</a>: all zones green? Any P0/P1 alerts in the alert bar?</li>
      <li><a href="/coop" class="step-link">Coop tab</a>: door opened overnight? Egg count entry for yesterday?</li>
      <li><a href="/recommendations" class="step-link">Recommendations tab</a>: any pending recommendations to approve or reject?</li>
    </ul>
    <p><strong>Tips:</strong></p>
    <ul>
      <li>pH sensors need calibration every 2 weeks — the dashboard will remind you</li>
      <li>You can enable push notifications (ntfy) in <a href="/settings/notifications" class="step-link">Settings → Notifications</a></li>
      <li>The AI engine improves over time as it accumulates GOOD-quality sensor data</li>
    </ul>
    <p>Thank you for setting up your farm platform. The hardware docs are at <code>docs/</code> and the reference documentation covers every screen in detail.</p>
    <p class="restart-hint"><button class="btn-text" onclick={restartTutorial}>Restart Tutorial from the beginning</button></p>
  </div>
  <div class="step-actions">
    <a href="/tutorial/{STEP - 1}" class="btn-secondary">
      <ChevronLeft size={16} /> Back
    </a>
    <button class="btn-primary" onclick={markDone}>
      Finish <CheckCircle size={16} />
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
  .step-body strong { color: var(--color-text); }
  code {
    background: var(--color-bg);
    border-radius: 3px;
    padding: 2px 5px;
    font-size: 13px;
    font-family: 'Courier New', monospace;
    color: var(--color-text);
  }
  .step-link {
    color: var(--color-accent);
    text-decoration: none;
  }
  .step-link:hover { text-decoration: underline; }
  .restart-hint { margin-top: var(--spacing-md); }
  .btn-text {
    background: none;
    border: none;
    color: var(--color-muted);
    font-size: 13px;
    font-family: 'Inter', system-ui, sans-serif;
    cursor: pointer;
    padding: 0;
    text-decoration: underline;
  }
  .btn-text:hover { color: var(--color-text-secondary); }
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
