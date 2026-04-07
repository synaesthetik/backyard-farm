<script lang="ts">
  import { formatElapsed } from './ws.svelte';
  import type { NodeState } from './types';

  interface Props {
    node: NodeState;
    isOffline: boolean;
  }

  let { node, isOffline }: Props = $props();

  function heartbeatCopy(): string {
    if (!node.last_seen) return 'Never reported';
    const elapsed = Date.now() - new Date(node.last_seen).getTime();
    const seconds = Math.floor(elapsed / 1000);
    if (isOffline) {
      const minutes = Math.floor(seconds / 60);
      return `Last seen ${minutes}m ago`;
    }
    if (seconds > 90) {
      const minutes = Math.floor(seconds / 60);
      return `Last seen ${minutes}m ago`;
    }
    return `Heartbeat ${seconds}s ago`;
  }
</script>

<div class="node-row">
  <div class="node-left">
    <span
      class="status-dot"
      class:online={!isOffline}
      class:offline={isOffline}
    ></span>
    <span class="node-name">{node.node_id}</span>
  </div>
  <div class="node-right">
    <span class="heartbeat-text">{heartbeatCopy()}</span>
    {#if isOffline}
      <span class="status-badge offline-badge">OFFLINE</span>
    {:else}
      <span class="status-badge online-badge">ONLINE</span>
    {/if}
  </div>
</div>

<style>
  .node-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--spacing-sm) 0;
  }

  .node-left {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .status-dot.online {
    background-color: #4ade80;
  }

  .status-dot.offline {
    background-color: #ef4444;
  }

  .node-name {
    font-size: 16px;
    font-weight: 400;
    color: var(--color-text-primary);
  }

  .node-right {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .heartbeat-text {
    font-size: 14px;
    font-weight: 400;
    color: var(--color-text-secondary);
  }

  .status-badge {
    display: inline-block;
    font-size: 12px;
    font-weight: 400;
    padding: 2px var(--spacing-xs);
    border-radius: 4px;
    line-height: 1.4;
    /* 44px touch target via padding on the parent row */
  }

  .online-badge {
    color: #4ade80;
    background: none;
  }

  .offline-badge {
    background-color: #ef4444;
    color: #f1f5f9;
  }
</style>
