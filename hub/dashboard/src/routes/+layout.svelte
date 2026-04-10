<script>
  import '../app.css';
  import { onMount } from 'svelte';
  import { dashboardStore } from '$lib/ws.svelte';
  import TabBar from '$lib/TabBar.svelte';
  import AlertBar from '$lib/AlertBar.svelte';
  import Toast from '$lib/Toast.svelte';

  let { children } = $props();

  let toastMessage = $state('');
  let toastVisible = $state(false);

  function handleToast(event) {
    toastMessage = event.detail?.message ?? 'An error occurred';
    toastVisible = true;
  }

  onMount(() => {
    dashboardStore.connect();
    window.addEventListener('farm:toast', handleToast);

    return () => {
      dashboardStore.disconnect();
      window.removeEventListener('farm:toast', handleToast);
    };
  });
</script>

<div class="app-layout">
  <header class="app-header">
    <h1 class="header-title">Farm Dashboard</h1>
    <span
      class="ws-dot"
      class:connected={dashboardStore.connectionStatus === 'connected'}
      class:reconnecting={dashboardStore.connectionStatus === 'reconnecting'}
      title={dashboardStore.connectionStatus}
    ></span>
  </header>

  <TabBar />

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
    padding-bottom: var(--spacing-md);
  }
</style>
