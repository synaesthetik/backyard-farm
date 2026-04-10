<script lang="ts">
  import { page } from '$app/stores';
  import { Sprout, Home, Bell } from 'lucide-svelte';

  const tabs = [
    { path: '/', label: 'Zones', icon: Sprout, ariaLabel: 'Zones' },
    { path: '/coop', label: 'Coop', icon: Home, ariaLabel: 'Coop' },
    { path: '/recommendations', label: 'Recs', icon: Bell, ariaLabel: 'Recommendations' },
  ] as const;

  function isActive(tabPath: string, currentPath: string): boolean {
    if (tabPath === '/') return currentPath === '/' || currentPath.startsWith('/zones');
    return currentPath.startsWith(tabPath);
  }
</script>

<nav aria-label="Main navigation" class="tab-bar">
  {#each tabs as tab}
    <a
      href={tab.path}
      class="tab"
      class:active={isActive(tab.path, $page.url.pathname)}
      aria-current={isActive(tab.path, $page.url.pathname) ? 'page' : undefined}
      aria-label={tab.ariaLabel}
    >
      <tab.icon size={20} />
      <span class="tab-label">{tab.label}</span>
    </a>
  {/each}
</nav>

<style>
  .tab-bar {
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    display: flex;
  }
  .tab {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-xs);
    min-height: 44px;
    text-decoration: none;
    color: var(--color-muted);
    font-size: 14px;
    font-weight: 400;
    line-height: 1.4;
    border-bottom: 2px solid transparent;
    transition: color 0.15s;
  }
  .tab.active {
    color: var(--color-accent);
    border-bottom-color: var(--color-accent);
  }
  .tab-label {
    font-size: 14px;
  }
</style>
