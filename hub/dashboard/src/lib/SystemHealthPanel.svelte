<script lang="ts">
  import NodeHealthRow from './NodeHealthRow.svelte';
  import type { NodeState } from './types';

  interface Props {
    nodes: Map<string, NodeState>;
  }

  let { nodes }: Props = $props();

  const OFFLINE_THRESHOLD_MS = 180 * 1000; // 3 * 60s (UI-SPEC: 3 missed heartbeats)

  function isNodeOffline(node: NodeState): boolean {
    if (!node.last_seen) return true;
    return Date.now() - new Date(node.last_seen).getTime() > OFFLINE_THRESHOLD_MS;
  }
</script>

<section class="system-health">
  <h2 class="panel-heading">System Health</h2>

  {#if nodes.size === 0}
    <p class="empty-state">No nodes connected</p>
  {:else}
    <div class="node-list">
      {#each [...nodes.values()] as node (node.node_id)}
        <NodeHealthRow {node} isOffline={isNodeOffline(node)} />
      {/each}
    </div>
  {/if}
</section>

<style>
  .system-health {
    background-color: var(--color-surface);
    padding: var(--spacing-md);
    border-radius: 8px;
  }

  .panel-heading {
    font-size: 20px;
    font-weight: 600;
    line-height: 1.2;
    color: var(--color-text-primary);
    margin-bottom: var(--spacing-md);
  }

  .empty-state {
    font-size: 16px;
    font-weight: 400;
    color: var(--color-muted);
  }

  .node-list {
    display: flex;
    flex-direction: column;
  }
</style>
