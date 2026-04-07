/** TypeScript types for the farm dashboard. */

export type QualityFlag = 'GOOD' | 'SUSPECT' | 'BAD';

export interface SensorReading {
  value: number;
  quality: QualityFlag;
  stuck: boolean;
  received_at: string; // ISO 8601
}

export interface ZoneState {
  zone_id: string;
  moisture: SensorReading | null;
  ph: SensorReading | null;
  temperature: SensorReading | null;
}

export interface NodeState {
  node_id: string;
  ts: string; // ISO 8601, last heartbeat time
  uptime_seconds: number;
  last_seen: string; // ISO 8601
}

export type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected';

export interface DashboardSnapshot {
  type: 'snapshot';
  zones: Record<string, Record<string, SensorReading>>;
  nodes: Record<string, NodeState>;
}

export interface SensorDelta {
  type: 'sensor_update';
  zone_id: string;
  sensor_type: string;
  value: number;
  quality: QualityFlag;
  stuck: boolean;
  received_at: string;
}

export interface HeartbeatDelta {
  type: 'heartbeat';
  node_id: string;
  ts: string;
  uptime_seconds: number;
}

export type WSMessage = DashboardSnapshot | SensorDelta | HeartbeatDelta;
