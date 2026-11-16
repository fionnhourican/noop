export interface Device {
  device_id: string;
  name?: string;
  model: string;
  serial?: string;
  firmware_version?: string;
  created_at: string;
}

export interface HeartRateSample {
  timestamp: string;
  bpm: number;
  source: string;
}

export interface RecoveryMetric {
  date: string;
  recovery_score: number;
  hrv_rmssd: number;
  resting_heart_rate: number;
  respiratory_rate?: number;
  skin_temp_deviation?: number;
  sleep_performance?: number;
  algorithm_version: string;
}

export interface StrainMetric {
  date: string;
  strain_score: number;
  average_hr?: number;
  max_hr?: number;
  kilojoules?: number;
  algorithm_version: string;
}

export interface SleepStage {
  stage: "awake" | "light" | "deep" | "rem" | string;
  start_time: string;
  end_time: string;
  duration_seconds: number;
}

export interface SleepSession {
  session_id: string;
  device_id: string;
  start_time: string;
  end_time: string;
  duration_seconds: number;
  deep_seconds?: number;
  light_seconds?: number;
  rem_seconds?: number;
  wake_seconds?: number;
  sleep_efficiency?: number;
  stages: SleepStage[];
}

export interface Workout {
  workout_id: string;
  start_time: string;
  end_time: string;
  duration_seconds: number;
  sport_name: string;
  strain_score?: number;
  avg_heart_rate?: number;
  max_heart_rate?: number;
}

export interface CollectorStatus {
  device_id: string;
  last_seen: string;
  connection_state: string;
  battery_percentage?: number;
  battery_millivolts?: number;
  is_charging?: boolean;
  queued_records: number;
  last_sync_timestamp?: string;
  agent_version: string;
}

export interface DashboardSummary {
  latest_heart_rate?: HeartRateSample;
  latest_recovery?: RecoveryMetric;
  latest_strain?: StrainMetric;
  latest_sleep?: SleepSession;
  collector_status?: CollectorStatus;
}

export interface LiveWebSocketMessage {
  type: "heart_rate" | "battery" | "status" | "pong" | string;
  timestamp?: string;
  bpm?: number;
  battery_level?: number;
  is_charging?: boolean;
  rr_intervals?: number[];
  device_id?: string;
}
