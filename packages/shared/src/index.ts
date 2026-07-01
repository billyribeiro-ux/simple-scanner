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
