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
    height: 48px;
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
    color: var(--color-text-primary);
  }
  .ws-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-offline);
    flex-shrink: 0;
  }
  .ws-dot.connected { background: var(--color-accent); }
  .ws-dot.reconnecting { background: var(--color-stale); }
  .page-content {
    flex: 1;
    padding: var(--spacing-md);
    padding-bottom: var(--spacing-md);
  }
</style>
