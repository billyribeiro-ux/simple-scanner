<script lang="ts">
  import { onMount } from 'svelte';
  import ArrowClockwiseIcon from 'phosphor-svelte/lib/ArrowClockwiseIcon';
  import ChartLineUpIcon from 'phosphor-svelte/lib/ChartLineUpIcon';
  import JsonPanel from '$lib/components/JsonPanel.svelte';
  import StatusBadge from '$lib/components/StatusBadge.svelte';
  import {
    checkDataFreshness,
    getDataQualityReport,
    getLatestFreshness,
    listFmpIngestionRuns,
    listQuoteSnapshots,
  } from '$lib/api';
  import { formatDateTime } from '$lib/governance';

  let report = $state<Record<string, unknown>>({ status: 'loading' });
  let freshness = $state<Record<string, unknown>>({ status: 'loading' });
  let quotes = $state<Record<string, unknown>>({ quote_snapshots: [] });
  let runs = $state<Record<string, unknown>>({ ingestion_runs: [] });
  let latestResult = $state<unknown>(null);
  let loading = $state(false);
  let symbols = $state('SPY,AAPL,NVDA');
  let intervals = $state('1min,5min,15min');

  function record(value: unknown): Record<string, unknown> {
    return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
  }

  function list(value: unknown): Record<string, unknown>[] {
    return Array.isArray(value) ? (value as Record<string, unknown>[]) : [];
  }

  async function refresh() {
    loading = true;
    const [nextReport, nextRuns, nextFreshness, nextQuotes] = await Promise.all([
      getDataQualityReport({ symbols, intervals }),
      listFmpIngestionRuns(),
      getLatestFreshness(),
      listQuoteSnapshots(symbols),
    ]);
    report = nextReport;
    runs = nextRuns;
    freshness = nextFreshness;
    quotes = nextQuotes;
    loading = false;
  }

  async function runFreshnessCheck() {
    loading = true;
    latestResult = await checkDataFreshness({
      symbols: symbols
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
      intervals: intervals
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
      include_quotes: true,
      persist: true,
    });
    await refresh();
  }

  onMount(() => {
    void refresh();
  });
</script>

<svelte:head>
  <title>Data Operations | Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <ChartLineUpIcon size={28} weight="duotone" />
    <div>
      <h1>Data Operations</h1>
      <p>Coverage, latest bars, dirty windows, and provider-source quality.</p>
    </div>
    <button class="btn" onclick={refresh} disabled={loading}>
      <ArrowClockwiseIcon size={18} />
      Refresh
    </button>
  </header>

  <section class="panel form-grid">
    <label class="field">Symbols <input bind:value={symbols} /></label>
    <label class="field">Intervals <input bind:value={intervals} /></label>
    <button class="btn primary" onclick={runFreshnessCheck} disabled={loading}>
      <ArrowClockwiseIcon size={18} />
      Check freshness
    </button>
  </section>

  <section class="grid">
    <div class="panel metric">
      <span>Bars</span>
      <strong>{record(record(report).summary).bar_count ?? 0}</strong>
      <small>{record(record(report).summary).latest_bar_group_count ?? 0} symbol intervals</small>
    </div>
    <div class="panel metric">
      <span>Missing windows</span>
      <strong>{record(record(report).summary).missing_bar_window_count ?? 0}</strong>
      <small>{record(record(report).summary).dirty_pipeline_window_count ?? 0} dirty windows</small>
    </div>
    <div class="panel metric">
      <span>Provider errors</span>
      <strong>{record(record(report).summary).provider_error_count ?? 0}</strong>
      <small
        >{record(record(report).summary).provider_capability_warning_count ?? 0} capability warnings</small
      >
    </div>
    <div class="panel metric">
      <span>Freshness</span>
      <StatusBadge value={String(record(freshness).status ?? 'not checked')} />
      <small>{formatDateTime(record(freshness).generated_at as string)}</small>
    </div>
    <div class="panel metric">
      <span>Quote snapshots</span>
      <strong>{list(record(quotes).quote_snapshots).length}</strong>
      <small>Durable latest rows</small>
    </div>
    <div class="panel metric">
      <span>Ingestion runs</span>
      <strong>{record(record(report).summary).ingestion_run_count ?? 0}</strong>
      <small>FMP source coverage</small>
    </div>
  </section>

  <section class="panel">
    <h2>Quote snapshots</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Price</th>
            <th>Volume</th>
            <th>Timestamp</th>
            <th>Flags</th>
          </tr>
        </thead>
        <tbody>
          {#each list(record(quotes).quote_snapshots) as quote}
            <tr>
              <td class="mono">{quote.symbol}</td>
              <td>{quote.price ?? '-'}</td>
              <td>{quote.volume ?? '-'}</td>
              <td>{formatDateTime(quote.timestamp_utc as string)}</td>
              <td>{JSON.stringify(quote.data_quality_flags ?? [])}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section class="panel">
    <h2>Latest bars</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Interval</th>
            <th>Count</th>
            <th>Latest</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {#each list(record(report).latest_bars) as row}
            <tr>
              <td class="mono">{row.symbol}</td>
              <td>{row.interval}</td>
              <td>{row.bar_count ?? 0}</td>
              <td>{formatDateTime(row.latest_bar_timestamp_utc as string)}</td>
              <td>{JSON.stringify(row.source_breakdown ?? {})}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section class="panel">
    <h2>Ingestion history</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Run</th>
            <th>Type</th>
            <th>Status</th>
            <th>Fetched</th>
            <th>Completed</th>
          </tr>
        </thead>
        <tbody>
          {#each list(record(runs).ingestion_runs) as run}
            <tr>
              <td class="mono">{run.ingestion_run_id}</td>
              <td>{run.ingestion_type}</td>
              <td><StatusBadge value={String(run.status ?? 'UNKNOWN')} /></td>
              <td>{run.records_fetched ?? 0}</td>
              <td>{formatDateTime(run.completed_at as string)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  {#if list(record(report).warnings).length}
    <section class="panel">
      <h2>Warnings</h2>
      <ul>
        {#each list(record(report).warnings) as warning}
          <li>{warning}</li>
        {/each}
      </ul>
    </section>
  {/if}

  <section class="panel">
    <JsonPanel title="Freshness report" value={latestResult ?? freshness} />
    <JsonPanel title="Quality report" value={report} />
  </section>
</div>

<style>
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
  }

  header > div {
    display: grid;
    gap: 4px;
  }

  h1,
  h2,
  p,
  ul {
    margin: 0;
  }

  p,
  small,
  span,
  li {
    color: var(--muted);
  }

  .form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 14px;
  }

  .metric {
    display: grid;
    gap: 8px;
    min-height: 116px;
    align-content: start;
  }

  ul {
    padding-left: 18px;
  }
</style>
