<script>
  import '../app.css';
  import { onMount } from 'svelte';
  import { dashboardStore } from '$lib/ws.svelte';
  import TabBar from '$lib/TabBar.svelte';
  import AlertBar from '$lib/AlertBar.svelte';
  import Toast from '$lib/Toast.svelte';
  import { Settings } from 'lucide-svelte';

  let { children } = $props();

  let toastMessage = $state('');
  let toastVisible = $state(false);
  let showTutorialBanner = $state(false);

  function handleToast(event) {
    toastMessage = event.detail?.message ?? 'An error occurred';
    toastVisible = true;
  }

  function dismissWelcome() {
    localStorage.setItem('tutorial_welcome_dismissed', 'true');
    showTutorialBanner = false;
  }

  onMount(() => {
    dashboardStore.connect();
    window.addEventListener('farm:toast', handleToast);

    if (!localStorage.getItem('tutorial_completed') &&
        !localStorage.getItem('tutorial_welcome_dismissed')) {
      showTutorialBanner = true;
    }

    return () => {
      dashboardStore.disconnect();
      window.removeEventListener('farm:toast', handleToast);
    };
  });
</script>

<div class="app-layout">
  <header class="app-header">
    <h1 class="header-title">Farm Dashboard</h1>
    <div class="header-right">
      <a href="/settings/ai" class="settings-link" aria-label="Open AI settings">
        <Settings size={20} />
      </a>
      <span
        class="ws-dot"
        class:connected={dashboardStore.connectionStatus === 'connected'}
        class:reconnecting={dashboardStore.connectionStatus === 'reconnecting'}
        title={dashboardStore.connectionStatus}
      ></span>
    </div>
  </header>

  <TabBar />

  {#if showTutorialBanner}
    <div class="tutorial-banner" role="banner">
      <span class="tutorial-banner-text">
        New to Backyard Farm? Take the interactive tutorial to get up and running.
      </span>
      <div class="tutorial-banner-actions">
        <a href="/tutorial/1" class="tutorial-banner-start">Start Tutorial</a>
        <button class="tutorial-banner-dismiss" onclick={dismissWelcome}>Skip</button>
      </div>
    </div>
  {/if}

  <AlertBar alerts={dashboardStore.alerts} />

  <main class="page-content">
    {@render children()}
  </main>
  <Toast message={toastMessage} bind:visible={toastVisible} />
</div>

<style>
  .app-layout {
    display: flex;
    flex-direction: column;
    min-height: 100dvh;
  }
  .app-header {
    position: sticky;
    top: 0;
    height: 52px;
    background: var(--color-surface);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 var(--spacing-md);
    z-index: 10;
    border-bottom: 1px solid var(--color-border);
  }
  .header-title {
    font-size: 20px;
    font-weight: 600;
    line-height: 1.2;
    color: var(--color-accent);
    letter-spacing: -0.01em;
  }
  .header-right {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .settings-link {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 44px;
    min-width: 44px;
    color: var(--color-muted);
    text-decoration: none;
    transition: color var(--transition-fast);
  }

  .settings-link:hover {
    color: var(--color-text-secondary);
  }

  .ws-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-offline);
    flex-shrink: 0;
    transition: background var(--transition-base), box-shadow var(--transition-base);
  }
  .ws-dot.connected {
    background: var(--color-accent);
    box-shadow: 0 0 6px rgba(74, 222, 128, 0.5);
  }
  .ws-dot.reconnecting {
    background: var(--color-stale);
    animation: pulse 1.5s ease-in-out infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  .page-content {
    flex: 1;
    padding: var(--spacing-md);
    width: 100%;
    max-width: 1280px;
    margin: 0 auto;
  }

  @media (min-width: 640px) {
    .page-content {
      padding: var(--spacing-lg) var(--spacing-xl);
    }
  }

  @media (min-width: 1024px) {
    .page-content {
      padding: var(--spacing-lg) var(--spacing-2xl);
    }
  }

  .tutorial-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--spacing-md);
    padding: var(--spacing-sm) var(--spacing-md);
    background: color-mix(in srgb, var(--color-accent) 12%, var(--color-surface));
    border-bottom: 1px solid color-mix(in srgb, var(--color-accent) 30%, var(--color-border));
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 13px;
    flex-wrap: wrap;
  }
  .tutorial-banner-text { color: var(--color-text-secondary); flex: 1; min-width: 200px; }
  .tutorial-banner-actions { display: flex; gap: var(--spacing-sm); align-items: center; }
  .tutorial-banner-start {
    color: var(--color-accent);
    font-weight: 600;
    text-decoration: none;
    padding: 4px 12px;
    border: 1px solid var(--color-accent);
    border-radius: 4px;
  }
  .tutorial-banner-start:hover { background: color-mix(in srgb, var(--color-accent) 10%, transparent); }
  .tutorial-banner-dismiss {
    color: var(--color-muted);
    background: none;
    border: none;
    cursor: pointer;
    padding: 4px 8px;
    font-size: 13px;
    font-family: inherit;
  }
  .tutorial-banner-dismiss:hover { color: var(--color-text-secondary); }
</style>
