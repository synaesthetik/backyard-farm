<script lang="ts">
  import { page } from '$app/stores';

  let { children } = $props();

  const tabs = [
    { label: 'AI', href: '/settings/ai' },
    { label: 'Calibration', href: '/settings/calibration' },
    { label: 'Notifications', href: '/settings/notifications' },
    { label: 'Storage', href: '/settings/storage' },
  ];

  const pathname = $derived($page.url.pathname);
</script>

<div class="settings-layout">
  <nav class="settings-nav" aria-label="Settings sections">
    {#each tabs as tab}
      <a
        href={tab.href}
        class="settings-tab"
        class:active={pathname === tab.href}
        aria-current={pathname === tab.href ? 'page' : undefined}
      >
        {tab.label}
      </a>
    {/each}
  </nav>
  <div class="settings-content">
    {@render children()}
  </div>
</div>

<style>
  .settings-layout {
    display: flex;
    flex-direction: column;
  }

  .settings-nav {
    display: flex;
    gap: 0;
    border-bottom: 1px solid var(--color-border);
    margin-bottom: var(--spacing-md);
    overflow-x: auto;
  }

  .settings-tab {
    font-size: 14px;
    font-weight: 400;
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--color-muted);
    text-decoration: none;
    padding: var(--spacing-sm) var(--spacing-md);
    min-height: 44px;
    display: flex;
    align-items: center;
    border-bottom: 2px solid transparent;
    white-space: nowrap;
    transition: color var(--transition-fast), border-color var(--transition-fast);
  }

  .settings-tab:hover {
    color: var(--color-text-secondary);
  }

  .settings-tab.active {
    color: var(--color-accent);
    border-bottom-color: var(--color-accent);
  }

  .settings-content {
    flex: 1;
  }
</style>
