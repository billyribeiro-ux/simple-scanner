export type {
  ActivationResponse,
  AppConfig,
  DecisionLedgerEvent,
  ExportMetadata,
  HealthStatus,
  ModelProposal,
  ResearchCycle,
  ResearchCycleArtifact,
  ResearchStatus,
  Signal,
} from '@amd/shared';

export type ProviderHealth = {
  status: string;
  warning?: string;
  requests?: number;
};

export type ScannerStatus = {
  running: boolean;
  started_at: string | null;
  latest_count: number;
  last_error: string | null;
};
