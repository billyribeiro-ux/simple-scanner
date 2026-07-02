import { z } from 'zod';

export const sideSchema = z.enum(['LONG', 'SHORT', 'NO_TRADE']);

export const signalSchema = z.object({
  timestamp: z.string(),
  ticker: z.string(),
  side: sideSchema,
  entry_price: z.number().nullable(),
  stop_price: z.number().nullable(),
  target_1: z.number().nullable(),
  target_2: z.number().nullable(),
  target_3: z.number().nullable(),
  risk_per_share: z.number().nullable(),
  reward_risk_to_t1: z.number().nullable(),
  reward_risk_to_t2: z.number().nullable(),
  reward_risk_to_t3: z.number().nullable(),
  expected_r: z.number(),
  confidence_score: z.number(),
  signal_grade: z.string(),
  setup_type: z.string(),
  market_regime: z.string(),
  ticker_regime: z.string(),
  reasons: z.array(z.string()),
  warnings: z.array(z.string()),
  historical_sample_size: z.number(),
  historical_win_rate: z.number(),
  historical_average_r: z.number(),
  model_version: z.string(),
  training_start: z.string().nullable(),
  training_end: z.string().nullable(),
  data_source: z.string(),
  status: z.string(),
  exit_price: z.number().nullable(),
  exit_reason: z.string().nullable(),
  realized_r: z.number().nullable()
});

export type Signal = z.infer<typeof signalSchema>;

export const configSchema = z.object({
  app_name: z.string(),
  default_symbols: z.array(z.string()),
  timezone: z.string(),
  min_confidence: z.number(),
  fmp_api_key_configured: z.boolean()
});

export type AppConfig = z.infer<typeof configSchema>;

export const jsonRecordSchema = z.record(z.string(), z.unknown());

export const healthSchema = z.object({
  status: z.string().optional(),
  time: z.string().optional(),
  persistence: jsonRecordSchema.optional()
});

export type HealthStatus = z.infer<typeof healthSchema>;

export const exportMetadataSchema = z.object({
  export_id: z.string().optional(),
  export_type: z.string().optional(),
  file_format: z.string().optional(),
  path: z.string().optional(),
  rows: z.number().optional(),
  source_id: z.string().nullable().optional(),
  file_sha256: z.string().nullable().optional(),
  workbook_sheets: z.array(z.string()).optional(),
  created_at: z.string().nullable().optional()
});

export type ExportMetadata = z.infer<typeof exportMetadataSchema>;

export const researchCycleSchema = z.object({
  research_cycle_id: z.string(),
  cycle_date: z.string().nullable().optional(),
  cycle_type: z.string().optional(),
  status: z.string(),
  symbols: z.array(z.string()).optional(),
  intervals: z.array(z.string()).optional(),
  start: z.string().nullable().optional(),
  end: z.string().nullable().optional(),
  session: z.string().nullable().optional(),
  active_model_version: z.string().nullable().optional(),
  challenger_model_version: z.string().nullable().optional(),
  proposal_ids: z.array(z.string()).optional(),
  comparison_ids: z.array(z.string()).optional(),
  data_quality_report_id: z.string().nullable().optional(),
  stale_window_status: jsonRecordSchema.optional(),
  summary: jsonRecordSchema.optional(),
  config: jsonRecordSchema.optional(),
  warnings: z.array(z.string()).optional(),
  config_hash: z.string().nullable().optional(),
  input_fingerprint: z.string().nullable().optional(),
  git_commit: z.string().nullable().optional(),
  database_revision: z.string().nullable().optional(),
  persistence_backend: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
  started_at: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
  failed_reason: z.string().nullable().optional()
});

export type ResearchCycle = z.infer<typeof researchCycleSchema>;

export const researchCycleArtifactSchema = z.object({
  cycle_artifact_id: z.string().optional(),
  artifact_id: z.string().optional(),
  research_cycle_id: z.string().optional(),
  artifact_type: z.string().optional(),
  source_id: z.string().nullable().optional(),
  source_table: z.string().nullable().optional(),
  payload: jsonRecordSchema.optional(),
  created_at: z.string().nullable().optional()
});

export type ResearchCycleArtifact = z.infer<typeof researchCycleArtifactSchema>;

export const championChallengerComparisonSchema = z.object({
  comparison_id: z.string().optional(),
  champion_model_version: z.string().nullable().optional(),
  challenger_model_version: z.string().nullable().optional(),
  delta_metrics: jsonRecordSchema.optional(),
  challenger_better_flags: z.array(z.string()).optional(),
  challenger_worse_flags: z.array(z.string()).optional(),
  gate_results: jsonRecordSchema.optional(),
  recommended_action: z.string().optional(),
  readiness_status: z.string().optional(),
  warnings: z.array(z.string()).optional(),
  created_at: z.string().nullable().optional()
});

export type ChampionChallengerComparison = z.infer<typeof championChallengerComparisonSchema>;

export const modelProposalSchema = z.object({
  proposal_id: z.string(),
  research_cycle_id: z.string().nullable().optional(),
  proposal_type: z.string().optional(),
  status: z.string(),
  champion_model_version: z.string().nullable().optional(),
  challenger_model_version: z.string().nullable().optional(),
  recommended_action: z.string().optional(),
  readiness_status: z.string().optional(),
  evidence_summary: jsonRecordSchema.optional(),
  champion_metrics: jsonRecordSchema.optional(),
  challenger_metrics: jsonRecordSchema.optional(),
  delta_metrics: jsonRecordSchema.optional(),
  pass_fail_gates: jsonRecordSchema.optional(),
  rejection_reasons: z.array(z.string()).optional(),
  approval_required: z.boolean().optional(),
  approved_by: z.string().nullable().optional(),
  approved_at: z.string().nullable().optional(),
  activation_model_version: z.string().nullable().optional(),
  activation_id: z.string().nullable().optional(),
  validation_report_ids: z.array(z.string()).optional(),
  calibration_audit_ids: z.array(z.string()).optional(),
  drift_report_ids: z.array(z.string()).optional(),
  model_review_report_ids: z.array(z.string()).optional(),
  comparison_ids: z.array(z.string()).optional(),
  replay_run_ids: z.array(z.string()).optional(),
  window_set_ids: z.array(z.string()).optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional()
});

export type ModelProposal = z.infer<typeof modelProposalSchema>;

export const decisionLedgerEventSchema = z.object({
  decision_id: z.string(),
  decision_type: z.string(),
  research_cycle_id: z.string().nullable().optional(),
  proposal_id: z.string().nullable().optional(),
  model_version: z.string().nullable().optional(),
  previous_model_version: z.string().nullable().optional(),
  decision_status: z.string().optional(),
  reason_codes: z.array(z.string()).optional(),
  evidence_refs: z.array(jsonRecordSchema).optional(),
  actor: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
  metadata: jsonRecordSchema.optional()
});

export type DecisionLedgerEvent = z.infer<typeof decisionLedgerEventSchema>;

export const schedulerJobSchema = z.object({
  job_id: z.string(),
  job_type: z.string(),
  status: z.string(),
  priority: z.number().optional(),
  scheduled_for: z.string().nullable().optional(),
  started_at: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
  failed_reason: z.string().nullable().optional(),
  payload: jsonRecordSchema.optional(),
  result: jsonRecordSchema.optional(),
  warnings: z.array(z.string()).optional(),
  research_cycle_id: z.string().nullable().optional(),
  created_by: z.string().nullable().optional(),
  lease_owner: z.string().nullable().optional(),
  lease_expires_at: z.string().nullable().optional(),
  heartbeat_at: z.string().nullable().optional(),
  attempt_count: z.number().nullable().optional(),
  max_attempts: z.number().nullable().optional(),
  timeout_seconds: z.number().nullable().optional(),
  last_error: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional()
});

export type SchedulerJob = z.infer<typeof schedulerJobSchema>;

export const schedulerJobEventSchema = z.object({
  event_id: z.string(),
  job_id: z.string(),
  event_type: z.string(),
  message: z.string(),
  metadata: jsonRecordSchema.optional(),
  created_at: z.string().nullable().optional()
});

export type SchedulerJobEvent = z.infer<typeof schedulerJobEventSchema>;

export const schedulerStatusSchema = z.object({
  status: z.string(),
  queued_jobs: z.number().optional(),
  running_jobs: z.number().optional(),
  failed_jobs: z.number().optional(),
  completed_jobs: z.number().optional(),
  cancelled_jobs: z.number().optional(),
  latest_job: schedulerJobSchema.nullable().optional(),
  latest_failed_job: schedulerJobSchema.nullable().optional(),
  latest_events: z.array(schedulerJobEventSchema).optional(),
  persistence_backend: z.string().nullable().optional(),
  warnings: z.array(z.string()).optional()
});

export type SchedulerStatus = z.infer<typeof schedulerStatusSchema>;

export const researchStatusSchema = z.object({
  status: z.string(),
  latest_research_cycle: researchCycleSchema.nullable().optional(),
  latest_model_proposal: modelProposalSchema.nullable().optional(),
  latest_scheduler_job: schedulerJobSchema.nullable().optional(),
  queued_scheduler_jobs: z.number().optional(),
  failed_scheduler_jobs: z.number().optional(),
  active_model_version: z.string().nullable().optional(),
  active_model_review_status: z.string().nullable().optional(),
  latest_calibration_drift_severity: z.string().nullable().optional(),
  stale_windows_summary: jsonRecordSchema.optional(),
  data_quality_summary: jsonRecordSchema.optional(),
  pending_proposals: z.array(modelProposalSchema).optional(),
  blocked_proposals: z.array(modelProposalSchema).optional(),
  last_successful_api_smoke_timestamp: z.string().nullable().optional(),
  warnings: z.array(z.string()).optional()
});

export type ResearchStatus = z.infer<typeof researchStatusSchema>;

export const activationResponseSchema = z.object({
  status: z.string().optional(),
  reason: z.string().optional(),
  proposal_id: z.string().optional(),
  proposal_status: z.string().optional(),
  activation: jsonRecordSchema.nullable().optional()
});

export type ActivationResponse = z.infer<typeof activationResponseSchema>;

export const apiErrorSchema = z.object({
  status: z.string().optional(),
  reason: z.string().optional(),
  detail: z.unknown().optional()
});

export type ApiError = z.infer<typeof apiErrorSchema>;
