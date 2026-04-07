/**
 * WebSocket reactive store for dashboard real-time updates (D-16).
 *
 * Connects to /ws/dashboard, receives snapshot on connect then deltas.
 * Stale logic runs client-side using received_at (INFRA-06).
 * Values are NOT cleared on disconnect — stale display is more useful than blank.
 */
import type { ZoneState, NodeState, SensorReading, ConnectionStatus, WSMessage } from './types';

const STALE_THRESHOLD_MS = 5 * 60 * 1000; // 5 minutes (INFRA-06)
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

class DashboardStore {
  zones = $state<Map<string, ZoneState>>(new Map());
  nodes = $state<Map<string, NodeState>>(new Map());
  connectionStatus = $state<ConnectionStatus>('disconnected');

  private ws: WebSocket | null = null;
  private reconnectDelay = RECONNECT_BASE_MS;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws/dashboard`;

    this.connectionStatus = 'reconnecting';
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.connectionStatus = 'connected';
      this.reconnectDelay = RECONNECT_BASE_MS;
    };

    this.ws.onmessage = (event) => {
      const msg: WSMessage = JSON.parse(event.data);
      this.handleMessage(msg);
    };

    this.ws.onclose = () => {
      this.connectionStatus = 'disconnected';
      // Do NOT clear zones/nodes — show stale data (D-16)
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  private handleMessage(msg: WSMessage) {
    if (msg.type === 'snapshot') {
      // Full state snapshot on connect
      const newZones = new Map<string, ZoneState>();
      for (const [zoneId, sensors] of Object.entries(msg.zones)) {
        newZones.set(zoneId, {
          zone_id: zoneId,
          moisture: sensors['moisture'] ?? null,
          ph: sensors['ph'] ?? null,
          temperature: sensors['temperature'] ?? null,
        });
      }
      this.zones = newZones;

      const newNodes = new Map<string, NodeState>();
      for (const [nodeId, state] of Object.entries(msg.nodes)) {
        newNodes.set(nodeId, { node_id: nodeId, ...state });
      }
      this.nodes = newNodes;
    } else if (msg.type === 'sensor_update') {
      const existing = this.zones.get(msg.zone_id) ?? {
        zone_id: msg.zone_id,
        moisture: null,
        ph: null,
        temperature: null,
      };

      const reading: SensorReading = {
        value: msg.value,
        quality: msg.quality,
        stuck: msg.stuck,
        received_at: msg.received_at,
      };

      const sensorKey = msg.sensor_type as keyof Pick<ZoneState, 'moisture' | 'ph' | 'temperature'>;
      if (sensorKey in existing) {
        (existing as any)[sensorKey] = reading;
      }

      // Reassign Map for Svelte 5 reactivity (Pitfall 4 from Research)
      this.zones = new Map(this.zones.set(msg.zone_id, { ...existing }));
    } else if (msg.type === 'heartbeat') {
      const node: NodeState = {
        node_id: msg.node_id,
        ts: msg.ts,
        uptime_seconds: msg.uptime_seconds,
        last_seen: msg.ts,
      };
      this.nodes = new Map(this.nodes.set(msg.node_id, node));
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, this.reconnectDelay);
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, RECONNECT_MAX_MS);
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }
}

export const dashboardStore = new DashboardStore();

/** Compute elapsed time string from ISO timestamp. */
export function formatElapsed(isoTimestamp: string): string {
  const elapsed = Date.now() - new Date(isoTimestamp).getTime();
  const seconds = Math.floor(elapsed / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ago`;
}

/** Check if a reading is stale (>= 5 minutes old). */
export function isStale(isoTimestamp: string): boolean {
  return Date.now() - new Date(isoTimestamp).getTime() >= STALE_THRESHOLD_MS;
}
