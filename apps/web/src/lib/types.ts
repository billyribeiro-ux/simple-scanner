export type { AppConfig, Signal } from '@amd/shared';

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
