<script lang="ts">
  import { goto } from '$app/navigation';
  import { ChevronLeft, ChevronRight } from 'lucide-svelte';

  const STEP = 2;
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

<svelte:head><title>Farm Tutorial — Step 2: First Boot Setup</title></svelte:head>

<div class="step-card">
  <h2 class="step-heading">First Boot Setup</h2>
  <div class="step-body">
    <p>On the hub machine (Pi 5 or mini-PC), run:</p>
    <pre class="code-block">git clone &lt;your-repo&gt;
cd backyard-farm
cp config/hub.env.example config/hub.env
# Edit config/hub.env: set MQTT_PASSWORD, TIMESCALE_PASSWORD, etc.
docker compose up -d
bash scripts/dev-init.sh  # creates DB schema and default zone</pre>
    <p>Then visit <code>https://&lt;hub-ip&gt;</code> in your browser. The dashboard should load over HTTPS.</p>
    <p>If you see a certificate warning, this is expected on first visit — accept it once and it won't appear again (Caddy uses a local CA).</p>
    <p>See <code>docs/hardware/hub.md</code> for hub assembly and power connections.</p>
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
  .code-block {
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: 4px;
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: 13px;
    font-family: 'Courier New', monospace;
    color: var(--color-text);
    overflow-x: auto;
    white-space: pre;
    margin: var(--spacing-sm) 0;
  }
  code {
    background: var(--color-bg);
    border-radius: 3px;
    padding: 2px 5px;
    font-size: 13px;
    font-family: 'Courier New', monospace;
    color: var(--color-text);
  }
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
