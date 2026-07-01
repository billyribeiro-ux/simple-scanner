<script lang="ts">
  import { fetchConfig, fetchProviderHealth, fetchScannerStatus, fetchSignals } from '$lib/api';
  import MetricCard from '$lib/components/MetricCard.svelte';
  import SignalTable from '$lib/components/SignalTable.svelte';
  import type { AppConfig, ProviderHealth, ScannerStatus, Signal } from '$lib/types';

  let config = $state<AppConfig | null>({
    app_name: 'Adaptive Market Decoder',
    default_symbols: ['AMZN', 'AAPL', 'TSLA', 'SPY', 'QQQ', 'IWM', 'NVDA', 'GOOGL', 'BABA', 'SHOP'],
    timezone: 'America/New_York',
    min_confidence: 0.7,
    fmp_api_key_configured: false,
  });
  let provider = $state<ProviderHealth>({ status: 'not checked' });
  let scanner = $state<ScannerStatus>({
    running: false,
    started_at: null,
    latest_count: 0,
    last_error: null,
  });
  let signals = $state<Signal[]>([]);

  const bestLong = $derived(signals.find((signal) => signal.side === 'LONG'));
  const bestShort = $derived(signals.find((signal) => signal.side === 'SHORT'));
  const avoidList = $derived(signals.filter((signal) => signal.side === 'NO_TRADE').slice(0, 5));

  async function refresh() {
    config = await fetchConfig();
    provider = await fetchProviderHealth();
    scanner = await fetchScannerStatus();
    signals = await fetchSignals();
  }
</script>

<svelte:head>
  <title>Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <div>
      <p>Market Decoder</p>
      <h1>Live signal command center</h1>
    </div>
    <button class="btn" onclick={refresh}>Refresh</button>
  </header>

  <section class="grid">
    <MetricCard
      title="Market Regime"
      value={signals[0]?.market_regime ?? 'Mixed/unknown'}
      detail="Live classifier"
      tone="amber"
    />
    <MetricCard
      title="Active Model"
      value={signals[0]?.model_version ?? 'Baseline'}
      detail="Versioned artifacts"
    />
    <MetricCard
      title="FMP Provider"
      value={provider.status}
      detail={config?.fmp_api_key_configured ? 'API key configured' : 'API key missing'}
    />
    <MetricCard
      title="Scanner"
      value={scanner.running ? 'Running' : 'Stopped'}
      detail={`${scanner.latest_count} recent signals`}
      tone={scanner.running ? 'green' : 'neutral'}
    />
  </section>

  <section class="grid">
    <div class="panel">
      <h2>Best Long</h2>
      <strong class="long">{bestLong?.ticker ?? '-'}</strong>
      <span>{bestLong?.setup_type ?? 'No active long'}</span>
    </div>
    <div class="panel">
      <h2>Best Short</h2>
      <strong class="short">{bestShort?.ticker ?? '-'}</strong>
      <span>{bestShort?.setup_type ?? 'No active short'}</span>
    </div>
    <div class="panel">
      <h2>Avoid List</h2>
      <div class="chips">
        {#if avoidList.length === 0}
          <span>No suppressions yet</span>
        {:else}
          {#each avoidList as signal}
            <span>{signal.ticker}</span>
          {/each}
        {/if}
      </div>
    </div>
  </section>

  <section>
    <h2>Live Signals</h2>
    <SignalTable {signals} />
  </section>
</div>

<style>
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
  }

  p {
    margin: 0 0 4px;
    color: var(--muted);
    text-transform: uppercase;
    font-size: 12px;
  }

  h1,
  h2 {
    margin: 0;
    letter-spacing: 0;
  }

  h1 {
    font-size: 30px;
  }

  h2 {
    font-size: 16px;
    margin-bottom: 12px;
  }

  .panel strong {
    display: block;
    font-size: 28px;
    margin-bottom: 6px;
  }

  .panel span,
  .chips span {
    color: var(--muted);
    font-size: 13px;
  }

  .long {
    color: var(--green);
  }

  .short {
    color: var(--red);
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
</style>
