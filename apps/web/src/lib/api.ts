import { configSchema, signalSchema, type AppConfig, type Signal } from '@amd/shared';
import type { ProviderHealth, ScannerStatus } from '$lib/types';

const API_BASE = 'http://localhost:8000';

async function getJson<T>(
  path: string,
  fallback: T,
  parser?: { parse: (value: unknown) => T },
): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${path}`);
    if (!response.ok) return fallback;
    const json = await response.json();
    return parser ? parser.parse(json) : (json as T);
  } catch {
    return fallback;
  }
}

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return (await response.json()) as T;
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

export async function fetchProviderHealth(): Promise<ProviderHealth> {
  return getJson('/provider/health', { status: 'offline' });
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
  return postJson('/scanner/start', { confidence_threshold });
}

export function stopScanner(): Promise<ScannerStatus> {
  return postJson('/scanner/stop');
}

export function exportSignalsCsv(): Promise<{ status: string; path: string }> {
  return postJson('/exports/signals.csv', { kind: 'signals' });
}

export function exportSignalsXlsx(): Promise<{ status: string; path: string }> {
  return postJson('/exports/signals.xlsx', { kind: 'signals' });
}
