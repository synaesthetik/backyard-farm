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

// Phase 2 types

export type HealthScore = 'green' | 'yellow' | 'red';
export type AlertSeverity = 'P0' | 'P1';
export type DoorState = 'open' | 'closed' | 'moving' | 'stuck';
export type IrrigationState = 'closed' | 'open' | 'moving';

export interface AlertEntry {
  key: string;
  severity: AlertSeverity;
  message: string;
  deep_link: string;
  count: number;
}

export interface Recommendation {
  recommendation_id: string;
  zone_id: string;
  rec_type: string;
  action_description: string;
  sensor_reading: string;
  explanation: string;
  source?: 'ai' | 'rules';
}

export interface AlertStateDelta {
  type: 'alert_state';
  alerts: AlertEntry[];
}

export interface RecommendationQueueDelta {
  type: 'recommendation_queue';
  recommendations: Recommendation[];
}

export interface ActuatorStateDelta {
  type: 'actuator_state';
  device: 'irrigation' | 'coop_door';
  zone_id?: string;
  state: string;
}

export interface ZoneHealthScoreDelta {
  type: 'zone_health_score';
  zone_id: string;
  score: HealthScore;
  contributing_sensors: string[];
}

export interface FeedLevelDelta {
  type: 'feed_level';
  percentage: number;
  below_threshold: boolean;
}

export interface WaterLevelDelta {
  type: 'water_level';
  percentage: number;
  below_threshold: boolean;
}

export interface CoopSchedule {
  open_at: string;
  close_at: string;
}

export interface CoopScheduleDelta {
  type: 'coop_schedule';
  schedule: CoopSchedule;
}

export interface DashboardSnapshot {
  type: 'snapshot';
  zones: Record<string, Record<string, SensorReading>>;
  nodes: Record<string, NodeState>;
  alerts: AlertEntry[];
  recommendations: Recommendation[];
  actuator_states: Record<string, string>;
  zone_health_scores: Record<string, { score: HealthScore; contributing_sensors: string[] }>;
  feed_level: { percentage: number; below_threshold: boolean } | null;
  water_level: { percentage: number; below_threshold: boolean } | null;
  coop_schedule: CoopSchedule | null;
  egg_count: { today: number; hen_present: boolean; raw_weight_grams: number | null; updated_at: string } | null;
  feed_consumption: { rate_grams_per_day: number; weekly: number[] } | null;
  model_maturity: ModelMaturityEntry[] | null;
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

export type WSMessage =
  | DashboardSnapshot
  | SensorDelta
  | HeartbeatDelta
  | AlertStateDelta
  | RecommendationQueueDelta
  | ActuatorStateDelta
  | ZoneHealthScoreDelta
  | FeedLevelDelta
  | WaterLevelDelta
  | CoopScheduleDelta
  | NestingBoxDelta
  | FeedConsumptionDelta
  | ModelMaturityDelta;

// Phase 3 types

export interface FlockConfig {
  breed: string;
  lay_rate_override: number | null;
  hatch_date: string;
  flock_size: number;
  supplemental_lighting: boolean;
  hen_weight_threshold_grams: number;
  egg_weight_grams: number;
  tare_weight_grams: number;
  latitude: number;
  longitude: number;
}

export interface NestingBoxDelta {
  type: 'nesting_box';
  estimated_count: number;
  hen_present: boolean;
  raw_weight_grams: number;
  updated_at: string;
}

export interface FeedConsumptionDelta {
  type: 'feed_consumption';
  rate_grams_per_day: number;
  weekly: number[];
}

// Phase 4 types

export type AIDomain = 'irrigation' | 'zone_health' | 'flock_anomaly';
export type AIMode = 'ai' | 'rules';

export interface ModelMaturityEntry {
  domain: AIDomain;
  mode: AIMode;
  weeks_of_data: number;
  good_flag_ratio: number;
  recommendation_count: number;
  approved_count: number;
  rejected_count: number;
  gate_passed: boolean;
}

export interface ModelMaturityDelta {
  type: 'model_maturity';
  entries: ModelMaturityEntry[];
}
