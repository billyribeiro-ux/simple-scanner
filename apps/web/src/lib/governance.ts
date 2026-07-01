import type { ApiFailure } from '$lib/api';

export const ACTIVATION_CONFIRMATION_PHRASE = 'ACTIVATE SCANNER MODEL';

export function isApiFailure(value: unknown): value is ApiFailure {
  return Boolean(
    value &&
    typeof value === 'object' &&
    (value as { status?: unknown }).status === 'error' &&
    typeof (value as { reason?: unknown }).reason === 'string',
  );
}

export function normalizeSymbolsInput(value: string): string[] {
  return value
    .split(',')
    .map((symbol) => symbol.trim().toUpperCase())
    .filter(Boolean)
    .map((symbol) => (symbol === 'APPL' ? 'AAPL' : symbol));
}

export function formatList(items: string[] | null | undefined, fallback = 'None'): string {
  if (!items?.length) return fallback;
  return items.join(', ');
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return date.toLocaleString();
}

export function compactId(value: string | null | undefined): string {
  if (!value) return '-';
  if (value.length <= 18) return value;
  return `${value.slice(0, 8)}...${value.slice(-6)}`;
}

export function prettyJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2);
}

export function safeExportSummary(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object') return {};
  const entries = Object.entries(value as Record<string, unknown>).filter(
    ([key]) => !['path', 'absolute_path', 'local_path'].includes(key),
  );
  return Object.fromEntries(entries);
}
