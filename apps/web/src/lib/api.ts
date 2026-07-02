import { env } from '$env/dynamic/public';
import {
  configSchema,
  decisionLedgerEventSchema,
  exportMetadataSchema,
  healthSchema,
  modelProposalSchema,
  researchCycleArtifactSchema,
  researchCycleSchema,
  researchStatusSchema,
  schedulerJobEventSchema,
  schedulerJobSchema,
  schedulerStatusSchema,
  signalSchema,
  type ActivationResponse,
  type AppConfig,
  type DecisionLedgerEvent,
  type ExportMetadata,
  type HealthStatus,
  type ModelProposal,
  type ResearchCycle,
  type ResearchCycleArtifact,
  type ResearchStatus,
  type SchedulerJob,
  type SchedulerJobEvent,
  type SchedulerStatus,
  type Signal,
} from '@amd/shared';
import type { ProviderHealth, ScannerStatus } from '$lib/types';

const API_BASE = env.PUBLIC_API_BASE_URL || 'http://localhost:8000';

type Parser<T> = { parse: (value: unknown) => T };

export type ApiFailure = {
  status: 'error';
  reason: string;
};

export type ResearchCycleCreatePayload = {
  cycle_date?: string;
  cycle_type?: string;
  symbols?: string[];
  intervals?: Array<'1min' | '5min' | '15min'>;
  start?: string;
  end?: string;
  session?: string;
  active_model_version?: string;
  challenger_model_version?: string;
  allow_stale?: boolean;
  refresh_data?: boolean;
  max_window_count?: number;
  run_now?: boolean;
};

export type ResearchCycleRunPayload = {
  allow_stale?: boolean;
  refresh_data?: boolean;
  export_reports?: boolean;
};

export type ProposalDecisionPayload = {
  actor?: string;
  reason_codes?: string[];
};

export type ProposalActivationPayload = {
  actor?: string;
  confirm_manual_activation: boolean;
  validation_mode?: string;
  calibration_audit_required?: boolean;
};

export type DecisionLedgerFilters = {
  model_version?: string;
  proposal_id?: string;
  research_cycle_id?: string;
  decision_type?: string;
  start?: string;
  end?: string;
};

export type ExportResponse = {
  status: string;
  export?: ExportMetadata;
};

export type SchedulerJobCreatePayload = {
  job_type:
    | 'research_cycle_dry_run'
    | 'research_cycle_run'
    | 'data_quality_report'
    | 'export_research_cycle'
    | 'export_operations_status'
    | 'fmp_capability_check'
    | 'fmp_quote_snapshot'
    | 'fmp_eod_refresh'
    | 'fmp_intraday_refresh'
    | 'fmp_incremental_intraday_refresh';
  payload?: Record<string, unknown>;
  priority?: number;
  scheduled_for?: string;
  created_by?: string;
};

export type FmpActionPayload = {
  symbols?: string[];
  intervals?: string[];
  endpoint_keys?: string[];
  include_websocket?: boolean;
  start?: string;
  end?: string;
};

async function getJson<T>(path: string, fallback: T, parser?: Parser<T>): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${path}`);
    if (!response.ok) return fallback;
    const json = await response.json();
    return parser ? parser.parse(json) : (json as T);
  } catch {
    return fallback;
  }
}

async function requestJson<T>(
  path: string,
  options: RequestInit = {},
  fallback: T,
  parser?: Parser<T>,
): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        'content-type': 'application/json',
        ...(options.headers ?? {}),
      },
    });
    const json = (await response.json()) as unknown;
    if (!response.ok) return fallback;
    return parser ? parser.parse(json) : (json as T);
  } catch {
    return fallback;
  }
}

async function postJson<T>(
  path: string,
  body: unknown | undefined,
  fallback: T,
  parser?: Parser<T>,
) {
  return requestJson(
    path,
    {
      method: 'POST',
      body: body === undefined ? undefined : JSON.stringify(body),
    },
    fallback,
    parser,
  );
}

function queryString(filters: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== '') params.set(key, String(value));
  }
  const query = params.toString();
  return query ? `?${query}` : '';
}

export async function fetchConfig(): Promise<AppConfig> {
  return getJson(
    '/config',
    {
      app_name: 'Adaptive Market Decoder',
      default_symbols: [
        'AMZN',
        'AAPL',
        'TSLA',
        'SPY',
        'QQQ',
        'IWM',
        'NVDA',
        'GOOGL',
        'BABA',
        'SHOP',
      ],
      timezone: 'America/New_York',
      min_confidence: 0.7,
      fmp_api_key_configured: false,
    },
    configSchema,
  );
}

export async function getHealth(): Promise<HealthStatus> {
  return getJson('/health', { status: 'offline' }, healthSchema);
}

export const getConfig = fetchConfig;

export async function fetchProviderHealth(): Promise<ProviderHealth> {
  return getJson('/provider/health', { status: 'offline' });
}

export async function getProviderStatus(): Promise<Record<string, unknown>> {
  return getJson('/operations/provider-status', { status: 'offline' });
}

export async function getProviderCapabilities(): Promise<Record<string, unknown>> {
  return getJson('/provider/capabilities', { provider: 'fmp', latest_capabilities: [] });
}

export async function checkProviderCapabilities(
  payload: FmpActionPayload,
): Promise<Record<string, unknown>> {
  return postJson('/provider/capabilities/check', payload, { status: 'error' });
}

export async function runFmpSmoke(): Promise<Record<string, unknown>> {
  return postJson('/provider/fmp/smoke', undefined, { status: 'error' });
}

export async function ingestFmpQuotes(payload: FmpActionPayload): Promise<Record<string, unknown>> {
  return postJson('/data/ingest/fmp/quotes', payload, { status: 'error' });
}

export async function ingestFmpEod(payload: FmpActionPayload): Promise<Record<string, unknown>> {
  return postJson('/data/ingest/fmp/eod', payload, { status: 'error' });
}

export async function ingestFmpIntraday(
  payload: FmpActionPayload,
): Promise<Record<string, unknown>> {
  return postJson('/data/ingest/fmp/intraday', payload, { status: 'error' });
}

export async function ingestFmpIncrementalIntraday(
  payload: FmpActionPayload,
): Promise<Record<string, unknown>> {
  return postJson('/data/ingest/fmp/incremental-intraday', payload, { status: 'error' });
}

export async function listFmpIngestionRuns(): Promise<Record<string, unknown>> {
  return getJson('/data/ingestion-runs', { ingestion_runs: [] });
}

export async function getDataQualityReport(
  params: {
    symbols?: string;
    intervals?: string;
    start?: string;
    end?: string;
  } = {},
): Promise<Record<string, unknown>> {
  return getJson(`/data/quality-report${queryString(params)}`, { status: 'offline' });
}

export async function fetchScannerStatus(): Promise<ScannerStatus> {
  return getJson('/scanner/status', {
    running: false,
    started_at: null,
    latest_count: 0,
    last_error: null,
  });
}

export async function fetchSignals(): Promise<Signal[]> {
  return getJson('/signals/live', [], {
    parse: (value) => signalSchema.array().parse(value),
  });
}

export function startScanner(confidence_threshold: number): Promise<ScannerStatus> {
  return postJson(
    '/scanner/start',
    { confidence_threshold },
    {
      running: false,
      started_at: null,
      latest_count: 0,
      last_error: 'scanner start failed',
    },
  );
}

export function stopScanner(): Promise<ScannerStatus> {
  return postJson('/scanner/stop', undefined, {
    running: false,
    started_at: null,
    latest_count: 0,
    last_error: 'scanner stop failed',
  });
}

export function exportSignalsCsv(): Promise<{ status: string; path: string }> {
  return postJson('/exports/signals.csv', { kind: 'signals' }, { status: 'error', path: '' });
}

export function exportSignalsXlsx(): Promise<{ status: string; path: string }> {
  return postJson('/exports/signals.xlsx', { kind: 'signals' }, { status: 'error', path: '' });
}

export async function getResearchStatus(): Promise<ResearchStatus> {
  return getJson('/operations/research-status', { status: 'offline' }, researchStatusSchema);
}

export async function getSchedulerStatus(): Promise<SchedulerStatus> {
  return getJson('/operations/scheduler-status', { status: 'offline' }, schedulerStatusSchema);
}

export async function listSchedulerJobs(
  params: {
    limit?: number;
    offset?: number;
    status?: string;
    job_type?: string;
  } = {},
): Promise<{ jobs: SchedulerJob[]; limit: number; offset: number }> {
  return getJson(
    `/scheduler/jobs${queryString(params)}`,
    { jobs: [], limit: params.limit ?? 100, offset: params.offset ?? 0 },
    {
      parse: (value) => {
        const payload = value as { jobs?: unknown; limit?: number; offset?: number };
        return {
          jobs: schedulerJobSchema.array().parse(payload.jobs ?? []),
          limit: payload.limit ?? params.limit ?? 100,
          offset: payload.offset ?? params.offset ?? 0,
        };
      },
    },
  );
}

export function createSchedulerJob(
  payload: SchedulerJobCreatePayload,
): Promise<SchedulerJob | ApiFailure> {
  return postJson('/scheduler/jobs', payload, {
    status: 'error',
    reason: 'scheduler job create failed',
  });
}

export function getSchedulerJob(job_id: string): Promise<SchedulerJob | ApiFailure> {
  return getJson(`/scheduler/jobs/${encodeURIComponent(job_id)}`, {
    status: 'error',
    reason: 'scheduler job not found',
  });
}

export function runSchedulerJob(job_id: string): Promise<SchedulerJob | ApiFailure> {
  return postJson(`/scheduler/jobs/${encodeURIComponent(job_id)}/run`, undefined, {
    status: 'error',
    reason: 'scheduler job run failed',
  });
}

export function cancelSchedulerJob(job_id: string): Promise<SchedulerJob | ApiFailure> {
  return postJson(`/scheduler/jobs/${encodeURIComponent(job_id)}/cancel`, undefined, {
    status: 'error',
    reason: 'scheduler job cancel failed',
  });
}

export function runPendingSchedulerJobs(max_jobs: number): Promise<Record<string, unknown>> {
  return postJson('/scheduler/jobs/run-pending', { max_jobs }, { status: 'error' });
}

export async function getSchedulerJobEvents(
  job_id: string,
): Promise<{ events: SchedulerJobEvent[]; limit: number; offset: number }> {
  return getJson(
    `/scheduler/jobs/${encodeURIComponent(job_id)}/events`,
    { events: [], limit: 500, offset: 0 },
    {
      parse: (value) => {
        const payload = value as { events?: unknown; limit?: number; offset?: number };
        return {
          events: schedulerJobEventSchema.array().parse(payload.events ?? []),
          limit: payload.limit ?? 500,
          offset: payload.offset ?? 0,
        };
      },
    },
  );
}

export async function listResearchCycles(
  params: {
    limit?: number;
    offset?: number;
    status?: string;
  } = {},
): Promise<{ research_cycles: ResearchCycle[]; limit: number; offset: number }> {
  return getJson(
    `/research/cycles${queryString(params)}`,
    { research_cycles: [], limit: params.limit ?? 100, offset: params.offset ?? 0 },
    {
      parse: (value) => {
        const payload = value as { research_cycles?: unknown; limit?: number; offset?: number };
        return {
          research_cycles: researchCycleSchema.array().parse(payload.research_cycles ?? []),
          limit: payload.limit ?? params.limit ?? 100,
          offset: payload.offset ?? params.offset ?? 0,
        };
      },
    },
  );
}

export function createResearchCycle(
  payload: ResearchCycleCreatePayload,
): Promise<ResearchCycle | ApiFailure> {
  return postJson('/research/cycles', payload, {
    status: 'error',
    reason: 'research cycle create failed',
  });
}

export function getResearchCycle(research_cycle_id: string): Promise<ResearchCycle | ApiFailure> {
  return getJson(`/research/cycles/${encodeURIComponent(research_cycle_id)}`, {
    status: 'error',
    reason: 'research cycle not found',
  });
}

export function dryRunResearchCycle(
  research_cycle_id: string,
): Promise<Record<string, unknown> | ApiFailure> {
  return postJson(`/research/cycles/${encodeURIComponent(research_cycle_id)}/dry-run`, undefined, {
    status: 'error',
    reason: 'dry-run failed',
  });
}

export function runResearchCycle(
  research_cycle_id: string,
  payload: ResearchCycleRunPayload,
): Promise<Record<string, unknown> | ApiFailure> {
  return postJson(`/research/cycles/${encodeURIComponent(research_cycle_id)}/run`, payload, {
    status: 'error',
    reason: 'research cycle run failed',
  });
}

export async function getResearchCycleArtifacts(
  research_cycle_id: string,
): Promise<{ artifacts: ResearchCycleArtifact[]; limit: number; offset: number }> {
  return getJson(
    `/research/cycles/${encodeURIComponent(research_cycle_id)}/artifacts`,
    { artifacts: [], limit: 500, offset: 0 },
    {
      parse: (value) => {
        const payload = value as { artifacts?: unknown; limit?: number; offset?: number };
        return {
          artifacts: researchCycleArtifactSchema.array().parse(payload.artifacts ?? []),
          limit: payload.limit ?? 500,
          offset: payload.offset ?? 0,
        };
      },
    },
  );
}

export function exportResearchCycle(
  research_cycle_id: string,
): Promise<Record<string, unknown> | ApiFailure> {
  return postJson(`/research/cycles/${encodeURIComponent(research_cycle_id)}/export`, undefined, {
    status: 'error',
    reason: 'research cycle export failed',
  });
}

export async function listModelProposals(
  params: {
    limit?: number;
    offset?: number;
    status?: string;
  } = {},
): Promise<{ model_proposals: ModelProposal[]; limit: number; offset: number }> {
  return getJson(
    `/research/model-proposals${queryString(params)}`,
    { model_proposals: [], limit: params.limit ?? 100, offset: params.offset ?? 0 },
    {
      parse: (value) => {
        const payload = value as { model_proposals?: unknown; limit?: number; offset?: number };
        return {
          model_proposals: modelProposalSchema.array().parse(payload.model_proposals ?? []),
          limit: payload.limit ?? params.limit ?? 100,
          offset: payload.offset ?? params.offset ?? 0,
        };
      },
    },
  );
}

export function getModelProposal(proposal_id: string): Promise<ModelProposal | ApiFailure> {
  return getJson(`/research/model-proposals/${encodeURIComponent(proposal_id)}`, {
    status: 'error',
    reason: 'model proposal not found',
  });
}

export function approveModelProposal(
  proposal_id: string,
  payload: ProposalDecisionPayload,
): Promise<ModelProposal | ApiFailure> {
  return postJson(`/research/model-proposals/${encodeURIComponent(proposal_id)}/approve`, payload, {
    status: 'error',
    reason: 'proposal approval failed',
  });
}

export function rejectModelProposal(
  proposal_id: string,
  payload: ProposalDecisionPayload,
): Promise<ModelProposal | ApiFailure> {
  return postJson(`/research/model-proposals/${encodeURIComponent(proposal_id)}/reject`, payload, {
    status: 'error',
    reason: 'proposal rejection failed',
  });
}

export function activateModelProposal(
  proposal_id: string,
  payload: ProposalActivationPayload,
): Promise<ActivationResponse | ApiFailure> {
  return postJson(
    `/research/model-proposals/${encodeURIComponent(proposal_id)}/activate`,
    payload,
    {
      status: 'error',
      reason: 'proposal activation failed',
    },
  );
}

export async function listDecisionLedger(
  filters: DecisionLedgerFilters = {},
): Promise<{ decisions: DecisionLedgerEvent[]; limit: number; offset: number }> {
  return getJson(
    `/research/decision-ledger${queryString({ ...filters, limit: 100, offset: 0 })}`,
    { decisions: [], limit: 100, offset: 0 },
    {
      parse: (value) => {
        const payload = value as { decisions?: unknown; limit?: number; offset?: number };
        return {
          decisions: decisionLedgerEventSchema.array().parse(payload.decisions ?? []),
          limit: payload.limit ?? 100,
          offset: payload.offset ?? 0,
        };
      },
    },
  );
}

export function triggerExport(kind: string, run_id: string): Promise<ExportResponse> {
  const endpoints: Record<string, string> = {
    'research-cycle-xlsx': '/exports/research-cycle.xlsx',
    'research-cycle-json': '/exports/research-cycle.json',
    'model-proposal-xlsx': '/exports/model-proposal.xlsx',
    'model-proposal-json': '/exports/model-proposal.json',
    'champion-challenger-comparison-xlsx': '/exports/champion-challenger-comparison.xlsx',
  };
  const path = endpoints[kind] ?? '/exports/research-cycle.xlsx';
  return postJson<ExportResponse>(
    path,
    { kind, run_id },
    { status: 'error' },
    {
      parse: (value) => {
        const payload = value as { status?: string; export?: unknown };
        return {
          status: payload.status ?? 'ok',
          export: payload.export ? exportMetadataSchema.parse(payload.export) : undefined,
        };
      },
    },
  );
}

export function getExportMetadata(export_id: string): Promise<ExportResponse> {
  return getJson<ExportResponse>(
    `/exports/${encodeURIComponent(export_id)}`,
    { status: 'not_found' },
    {
      parse: (value) => {
        const payload = value as { status?: string; export?: unknown };
        return {
          status: payload.status ?? 'ok',
          export: payload.export ? exportMetadataSchema.parse(payload.export) : undefined,
        };
      },
    },
  );
}
