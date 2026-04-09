import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import NodeHealthRow from './NodeHealthRow.svelte';
import type { NodeState } from './types';

afterEach(() => cleanup());

function makeNode(overrides: Partial<NodeState> = {}): NodeState {
  return {
    node_id: 'zone-1-node',
    ts: new Date().toISOString(),
    uptime_seconds: 3600,
    last_seen: new Date().toISOString(),
    ...overrides,
  };
}

describe('NodeHealthRow', () => {
  it('renders node_id text', () => {
    render(NodeHealthRow, { node: makeNode(), isOffline: false });
    expect(screen.getByText('zone-1-node')).toBeTruthy();
  });

  it('shows ONLINE badge when isOffline=false', () => {
    render(NodeHealthRow, { node: makeNode(), isOffline: false });
    expect(screen.getByText('ONLINE')).toBeTruthy();
  });

  it('shows OFFLINE badge when isOffline=true', () => {
    render(NodeHealthRow, { node: makeNode(), isOffline: true });
    expect(screen.getByText('OFFLINE')).toBeTruthy();
  });

  it('shows heartbeat elapsed text when online and last_seen is recent', () => {
    const fiveSecondsAgo = new Date(Date.now() - 5000).toISOString();
    render(NodeHealthRow, {
      node: makeNode({ last_seen: fiveSecondsAgo }),
      isOffline: false,
    });
    expect(screen.getByText(/Heartbeat.*ago/)).toBeTruthy();
  });

  it('shows "Last seen Nm ago" when offline', () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    render(NodeHealthRow, {
      node: makeNode({ last_seen: fiveMinutesAgo }),
      isOffline: true,
    });
    expect(screen.getByText(/Last seen.*ago/)).toBeTruthy();
  });
});
