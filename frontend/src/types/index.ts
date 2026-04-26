export interface SimulationScore {
  product: string;
  hook: string;
  angle: string;
  predicted_engagement: number;
  predicted_roas: number;
  predicted_ctr: number;
  corrected_roas: number;
  confidence: number;
  risk_score: number;
  rank_score: number;
  rank: number;
  ts: number;
}

export interface RuntimeSnapshot {
  ts: number;
  type: string;
  cycle: number;
  phase: "RESEARCH" | "EXPLORE" | "VALIDATE" | "SCALE";
  capital: number;
  avg_roas: number;
  win_rate: number;
  regime: string;
  signal_count: number;
  top_signals: Signal[];
  top_playbooks: Playbook[];
  patterns: Patterns;
  recent_decisions: Decision[];
  worker_status: Record<string, unknown>;
  simulation_scores: SimulationScore[];
}

export interface Signal {
  product: string;
  score: number;
  source: string;
  velocity?: number;
  platform?: string;
  category?: string;
}

export interface Playbook {
  product: string;
  phase: string;
  top_hooks: string[];
  top_angles: string[];
  estimated_roas: number;
  confidence: number;
  evidence_count: number;
  created_at: number;
}

export interface Patterns {
  hook_scores: Record<string, number>;
  angle_scores: Record<string, number>;
  regime_scores: Record<string, number>;
  top_hooks: string[];
  top_angles: string[];
}

export interface Decision {
  roas?: number;
  ctr?: number;
  cvr?: number;
  variant?: string | number;
  hook?: string;
  angle?: string;
  env_regime?: string;
  label?: string;
  eng_score?: number;
  capital?: number;
  cost?: number;
  revenue?: number;
}

export interface TaskRecord {
  name: string;
  kind: "thread" | "celery" | "scheduler" | "ws" | "state_writer" | "queue" | "loop" | "unknown";
  description: string;
  module: string;
  interval_s: number | null;
  last_run_ts: number | null;
  last_status: string;
  run_count: number;
  active: boolean;
  configured: boolean;
  next_run_ts: number | null;
  age_s: number | null;
}

export interface TaskInventory {
  type: "task_inventory";
  ts: number;
  summary: { total: number; active: number; idle: number; unconfigured: number; by_kind: Record<string, number> };
  tasks: TaskRecord[];
}

export interface HeartbeatEvent {
  type: "heartbeat";
  source: string;
  ts: number;
}

export interface MetricsIngestedEvent {
  type: "metrics.ingested";
  source: string;
  metrics: Record<string, number | string | boolean>;
  ts: number;
}

export interface RuntimeConsistencyEvent {
  type: "runtime.consistency";
  issues: string[];
  source: string;
  ts: number;
}

// Worker health — legacy "worker" and canonical "worker.health" both accepted
export type WorkerEvent =
  | { type: "worker";        worker: string; phase: string; status: string; ts: number }
  | { type: "worker.health"; worker: string; phase: string; status: string; ts: number };

// Tick — legacy "tick" and canonical "orchestrator.tick" both accepted
export type TickEvent =
  | { type: "tick";             phase: string; avg_roas: number; capital: number; win_rate?: number; ts: number }
  | { type: "orchestrator.tick"; phase: string; avg_roas: number; capital: number; win_rate?: number; ts: number };

// Snapshot — legacy "snapshot" and canonical "runtime.snapshot" both accepted
export type SnapshotEvent = RuntimeSnapshot & { type: "snapshot" | "runtime.snapshot" };

export type WsEvent =
  | SnapshotEvent
  | WorkerEvent
  | TickEvent
  | TaskInventory
  | HeartbeatEvent
  | MetricsIngestedEvent
  | RuntimeConsistencyEvent;
