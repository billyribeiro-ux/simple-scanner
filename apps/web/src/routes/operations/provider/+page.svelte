<script lang="ts">
  import { onMount } from 'svelte';
  import ArrowClockwiseIcon from 'phosphor-svelte/lib/ArrowClockwiseIcon';
  import DatabaseIcon from 'phosphor-svelte/lib/DatabaseIcon';
  import PlayIcon from 'phosphor-svelte/lib/PlayIcon';
  import ShieldCheckIcon from 'phosphor-svelte/lib/ShieldCheckIcon';
  import JsonPanel from '$lib/components/JsonPanel.svelte';
  import StatusBadge from '$lib/components/StatusBadge.svelte';
  import {
    checkProviderCapabilities,
    getCapabilityReviewSummary,
    getProviderStatus,
    ingestFmpEod,
    ingestFmpIncrementalIntraday,
    ingestFmpIntraday,
    ingestFmpQuotes,
    ingestFmpSeed,
    listFmpIngestionRuns,
    reviewProviderCapability,
    runFmpSmoke,
  } from '$lib/api';
  import { formatDateTime, normalizeSymbolsInput } from '$lib/governance';

  let status = $state<Record<string, unknown>>({ status: 'loading' });
  let reviewSummary = $state<Record<string, unknown>>({ status: 'loading' });
  let runs = $state<Record<string, unknown>>({ ingestion_runs: [] });
  let latestResult = $state<unknown>(null);
  let loading = $state(false);
  let symbols = $state('SPY,QQQ,AAPL,NVDA');
  let intervals = $state('1min,5min,15min');
  let start = $state(new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString());
  let end = $state(new Date().toISOString());
  let reviewer = $state('local-operator');
  let reviewNotes = $state('');
  let reviewStatus = $state('REVIEWED_ACCESSIBLE');

  function record(value: unknown): Record<string, unknown> {
    return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
  }

  function list(value: unknown): Record<string, unknown>[] {
    return Array.isArray(value) ? (value as Record<string, unknown>[]) : [];
  }

  function intervalList(): string[] {
    return intervals
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function payload() {
    return {
      symbols: normalizeSymbolsInput(symbols).slice(0, 10),
      intervals: intervalList(),
      start,
      end,
    };
  }

  async function refresh() {
    loading = true;
    const [nextStatus, nextRuns, nextReview] = await Promise.all([
      getProviderStatus(),
      listFmpIngestionRuns(),
      getCapabilityReviewSummary(),
    ]);
    status = nextStatus;
    runs = nextRuns;
    reviewSummary = nextReview;
    loading = false;
  }

  async function runAction(action: string) {
    loading = true;
    const body = payload();
    if (action === 'capability') latestResult = await checkProviderCapabilities(body);
    if (action === 'smoke') latestResult = await runFmpSmoke();
    if (action === 'quotes') latestResult = await ingestFmpQuotes(body);
    if (action === 'eod') latestResult = await ingestFmpEod(body);
    if (action === 'intraday') latestResult = await ingestFmpIntraday(body);
    if (action === 'incremental') latestResult = await ingestFmpIncrementalIntraday(body);
    if (action === 'seed-dry-run') {
      latestResult = await ingestFmpSeed({
        ...body,
        intervals: ['1day', ...intervalList()],
        dry_run: true,
      });
    }
    if (action === 'seed') {
      latestResult = await ingestFmpSeed({
        ...body,
        intervals: ['1day', ...intervalList()],
        dry_run: false,
      });
    }
    await refresh();
  }

  async function review(checkId: unknown) {
    if (!checkId) return;
    loading = true;
    latestResult = await reviewProviderCapability(String(checkId), {
      operator_review_status: reviewStatus as 'REVIEWED_ACCESSIBLE',
      reviewed_by: reviewer,
      review_notes: reviewNotes,
    });
    await refresh();
  }

  onMount(() => {
    void refresh();
  });
</script>

<svelte:head>
  <title>FMP Provider | Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <DatabaseIcon size={28} weight="duotone" />
    <div>
      <h1>FMP Provider</h1>
      <p>Entitlement checks, REST ingestion, and redacted provider accounting.</p>
    </div>
    <button class="btn" onclick={refresh} disabled={loading}>
      <ArrowClockwiseIcon size={18} />
      Refresh
    </button>
  </header>

  <section class="panel notice">
    <ShieldCheckIcon size={22} weight="duotone" />
    <div>
      <strong>Requires FMP_API_KEY</strong>
      <span>Data ingestion only. No broker execution.</span>
    </div>
  </section>

  <section class="grid">
    <div class="panel metric">
      <span>Key</span>
      <strong>{record(status).key_status ?? 'unknown'}</strong>
      <small>Runtime presence only</small>
    </div>
    <div class="panel metric">
      <span>REST</span>
      <StatusBadge value={record(status).rest_polling_default ? 'default' : 'unknown'} />
      <small>Polling path</small>
    </div>
    <div class="panel metric">
      <span>WebSocket probe</span>
      <StatusBadge value={record(status).websocket_probe_enabled ? 'enabled' : 'disabled'} />
      <small>Optional entitlement probe</small>
    </div>
    <div class="panel metric">
      <span>Review gate</span>
      <StatusBadge value={String(record(reviewSummary).status ?? 'unknown')} />
      <small>{record(reviewSummary).accessible_reviewed_count ?? 0} reviewed endpoints</small>
    </div>
    <div class="panel metric">
      <span>Latest ingestion</span>
      <strong>{record(record(status).latest_ingestion_run).status ?? '-'}</strong>
      <small
        >{formatDateTime(record(record(status).latest_ingestion_run).completed_at as string)}</small
      >
    </div>
  </section>

  <section class="panel form-grid">
    <label class="field wide">Symbols <input bind:value={symbols} /></label>
    <label class="field">Intervals <input bind:value={intervals} /></label>
    <label class="field wide">Start <input bind:value={start} /></label>
    <label class="field wide">End <input bind:value={end} /></label>
    <div class="toolbar wide">
      <button class="btn primary" onclick={() => runAction('capability')} disabled={loading}>
        <PlayIcon size={16} />
        Capability
      </button>
      <button class="btn" onclick={() => runAction('smoke')} disabled={loading}>Smoke</button>
      <button class="btn" onclick={() => runAction('quotes')} disabled={loading}>Quotes</button>
      <button class="btn" onclick={() => runAction('eod')} disabled={loading}>EOD</button>
      <button class="btn" onclick={() => runAction('intraday')} disabled={loading}>Intraday</button>
      <button class="btn" onclick={() => runAction('incremental')} disabled={loading}
        >Incremental</button
      >
      <button class="btn" onclick={() => runAction('seed-dry-run')} disabled={loading}
        >Seed dry-run</button
      >
      <button class="btn" onclick={() => runAction('seed')} disabled={loading}>Seed</button>
    </div>
  </section>

  <section class="panel form-grid">
    <label class="field">Reviewer <input bind:value={reviewer} /></label>
    <label class="field">
      Review
      <select bind:value={reviewStatus}>
        <option>REVIEWED_ACCESSIBLE</option>
        <option>REVIEWED_PARTIAL</option>
        <option>REVIEWED_BLOCKED</option>
        <option>REVIEWED_RATE_LIMITED</option>
        <option>REVIEWED_UNUSABLE</option>
        <option>UNREVIEWED</option>
      </select>
    </label>
    <label class="field wide">Notes <input bind:value={reviewNotes} /></label>
  </section>

  <section class="panel">
    <h2>Latest matrix</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Endpoint</th>
            <th>Status</th>
            <th>HTTP</th>
            <th>Rows</th>
            <th>Review</th>
            <th>Checked</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {#each list(record(status).latest_capabilities) as row}
            <tr>
              <td class="mono">{row.endpoint_key}</td>
              <td><StatusBadge value={String(row.status ?? 'UNKNOWN')} /></td>
              <td>{row.http_status ?? '-'}</td>
              <td>{row.sample_count ?? 0}</td>
              <td><StatusBadge value={String(row.operator_review_status ?? 'UNREVIEWED')} /></td>
              <td>{formatDateTime(row.checked_at as string)}</td>
              <td>
                <button class="btn small" onclick={() => review(row.check_id)} disabled={loading}
                  >Review</button
                >
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section class="panel">
    <h2>Ingestion runs</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Run</th>
            <th>Type</th>
            <th>Status</th>
            <th>Fetched</th>
            <th>Written</th>
          </tr>
        </thead>
        <tbody>
          {#each list(record(runs).ingestion_runs) as run}
            <tr>
              <td class="mono">{run.ingestion_run_id}</td>
              <td>{run.ingestion_type}</td>
              <td><StatusBadge value={String(run.status ?? 'UNKNOWN')} /></td>
              <td>{run.records_fetched ?? 0}</td>
              <td>{run.records_inserted ?? 0}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section class="panel">
    <JsonPanel title="Review summary" value={reviewSummary} />
    <JsonPanel title="Latest action" value={latestResult ?? status} />
  </section>
</div>

<style>
  header,
  .notice {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  header {
    justify-content: space-between;
    flex-wrap: wrap;
  }

  h1,
  h2,
  p {
    margin: 0;
  }

  p,
  small,
  span {
    color: var(--muted);
  }

  .metric {
    display: grid;
    gap: 8px;
    min-height: 116px;
    align-content: start;
  }

  .notice strong {
    display: block;
  }

  .form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 14px;
  }

  .small {
    min-height: 32px;
    padding: 6px 10px;
  }

  .wide {
    grid-column: span 2;
  }

  @media (max-width: 720px) {
    .wide {
      grid-column: span 1;
    }
  }
</style>
