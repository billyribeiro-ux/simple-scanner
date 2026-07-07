<script lang="ts">
  import { onMount } from 'svelte';
  import ArrowClockwiseIcon from 'phosphor-svelte/lib/ArrowClockwiseIcon';
  import FileArrowDownIcon from 'phosphor-svelte/lib/FileArrowDownIcon';
  import FlaskIcon from 'phosphor-svelte/lib/FlaskIcon';
  import PlayIcon from 'phosphor-svelte/lib/PlayIcon';
  import JsonPanel from '$lib/components/JsonPanel.svelte';
  import StatusBadge from '$lib/components/StatusBadge.svelte';
  import {
    createResearchCycle,
    dryRunResearchCycle,
    exportResearchCycle,
    listResearchCycles,
    runResearchCycle,
  } from '$lib/api';
  import {
    compactId,
    formatDateTime,
    formatList,
    isApiFailure,
    normalizeSymbolsInput,
    safeExportSummary,
  } from '$lib/governance';
  import type { ResearchCycle } from '$lib/types';

  let cycles = $state<ResearchCycle[]>([]);
  let loading = $state(false);
  let statusFilter = $state('');
  let message = $state('No cycle action requested.');
  let lastResult = $state<unknown>(null);

  let cycleDate = $state('2026-07-01');
  let cycleType = $state('daily');
  let symbols = $state('AMZN,AAPL,TSLA,SPY,QQQ,IWM,NVDA,GOOGL,BABA,SHOP');
  let symbolsInput = $state<HTMLInputElement | null>(null);
  let start = $state('2026-06-01T13:30');
  let end = $state('2026-06-30T20:00');
  let interval1 = $state(true);
  let interval5 = $state(true);
  let interval15 = $state(true);
  let activeModelVersion = $state('');
  let challengerModelVersion = $state('');
  let maxWindowCount = $state(20);
  let allowStale = $state(false);
  let refreshData = $state(false);
  let createReady = $state(false);

  function selectedIntervals(): Array<'1min' | '5min' | '15min'> {
    const intervals: Array<'1min' | '5min' | '15min'> = [];
    if (interval1) intervals.push('1min');
    if (interval5) intervals.push('5min');
    if (interval15) intervals.push('15min');
    return intervals.length ? intervals : ['1min'];
  }

  function localDateTime(value: string): string | undefined {
    return value ? new Date(value).toISOString() : undefined;
  }

  async function refresh() {
    loading = true;
    const payload = await listResearchCycles({ status: statusFilter || undefined });
    cycles = payload.research_cycles;
    loading = false;
  }

  async function createCycle() {
    message = 'Creating research cycle...';
    const requestedSymbols = symbolsInput?.value ?? symbols;
    try {
      const result = await createResearchCycle({
        cycle_date: cycleDate || undefined,
        cycle_type: cycleType,
        symbols: normalizeSymbolsInput(requestedSymbols),
        intervals: selectedIntervals(),
        start: localDateTime(start),
        end: localDateTime(end),
        session: 'rth',
        active_model_version: activeModelVersion || undefined,
        challenger_model_version: challengerModelVersion || undefined,
        allow_stale: allowStale,
        refresh_data: refreshData,
        max_window_count: maxWindowCount,
        run_now: false,
      });
      lastResult = result;
      message = isApiFailure(result)
        ? `Cycle create failed: ${result.reason}`
        : `Created research cycle ${result.research_cycle_id}`;
      await refresh();
    } catch (error) {
      message =
        error instanceof Error ? `Cycle create failed: ${error.message}` : 'Cycle create failed.';
    }
  }

  async function dryRun(id: string) {
    const result = await dryRunResearchCycle(id);
    lastResult = result;
    message = isApiFailure(result)
      ? `Dry-run failed: ${result.reason}`
      : `Dry-run completed for ${id}`;
  }

  async function runCycle(id: string) {
    const result = await runResearchCycle(id, {
      allow_stale: allowStale,
      refresh_data: refreshData,
      export_reports: false,
    });
    lastResult = result;
    message = isApiFailure(result)
      ? `Run failed: ${result.reason}`
      : `Run response received for ${id}`;
    await refresh();
  }

  async function exportCycle(id: string) {
    const result = await exportResearchCycle(id);
    lastResult = safeExportSummary(result);
    message = isApiFailure(result)
      ? `Export failed: ${result.reason}`
      : `Export metadata received for ${id}`;
  }

  onMount(() => {
    let detachCreate: (() => void) | undefined;
    const timer = window.setTimeout(() => {
      const button = document.getElementById('create-cycle-button');
      if (!button) return;
      const handleClick = () => {
        void createCycle();
      };
      button.addEventListener('click', handleClick);
      detachCreate = () => button.removeEventListener('click', handleClick);
      createReady = true;
    }, 0);
    void refresh();
    return () => {
      window.clearTimeout(timer);
      detachCreate?.();
      createReady = false;
    };
  });
</script>

<svelte:head>
  <title>Research Cycles | Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <FlaskIcon size={28} weight="duotone" />
    <div>
      <h1>Research cycles</h1>
      <p>Controlled research runs. Dry-run, run, and export are separate operator actions.</p>
    </div>
    <button class="btn" onclick={refresh} disabled={loading}>
      <ArrowClockwiseIcon size={18} />
      Refresh
    </button>
  </header>

  <section class="panel">
    <div class="form-grid">
      <label class="field">Cycle date <input type="date" bind:value={cycleDate} /></label>
      <label class="field">Cycle type <input bind:value={cycleType} /></label>
      <label class="field wide"
        >Symbols <input bind:this={symbolsInput} bind:value={symbols} /></label
      >
      <label class="field">Start <input type="datetime-local" bind:value={start} /></label>
      <label class="field">End <input type="datetime-local" bind:value={end} /></label>
      <label class="field"
        >Active model <input bind:value={activeModelVersion} placeholder="optional" /></label
      >
      <label class="field"
        >Challenger model <input
          bind:value={challengerModelVersion}
          placeholder="optional"
        /></label
      >
      <label class="field"
        >Max windows <input type="number" min="1" max="50" bind:value={maxWindowCount} /></label
      >
      <div class="field">
        Intervals
        <div class="checks">
          <label><input type="checkbox" bind:checked={interval1} /> 1min</label>
          <label><input type="checkbox" bind:checked={interval5} /> 5min</label>
          <label><input type="checkbox" bind:checked={interval15} /> 15min</label>
        </div>
      </div>
      <div class="field">
        Run flags
        <div class="checks">
          <label><input type="checkbox" bind:checked={allowStale} /> Allow stale</label>
          <label><input type="checkbox" bind:checked={refreshData} /> Refresh data</label>
        </div>
      </div>
      <div class="toolbar">
        <button id="create-cycle-button" class="btn primary" disabled={!createReady}>
          Create cycle
        </button>
      </div>
    </div>
  </section>

  <section class="panel toolbar">
    <label class="field"
      >Status filter
      <select bind:value={statusFilter} onchange={refresh}>
        <option value="">All</option>
        <option value="created">created</option>
        <option value="completed">completed</option>
        <option value="blocked">blocked</option>
        <option value="failed">failed</option>
      </select>
    </label>
    <span class="muted">{message}</span>
  </section>

  <section class="panel">
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Cycle</th>
            <th>Status</th>
            <th>Date range</th>
            <th>Symbols</th>
            <th>Models</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each cycles as cycle (cycle.research_cycle_id)}
            <tr>
              <td>
                <a class="link mono" href={`/research/cycles/${cycle.research_cycle_id}`}>
                  {compactId(cycle.research_cycle_id)}
                </a>
                <div class="muted">{formatDateTime(cycle.created_at)}</div>
              </td>
              <td><StatusBadge value={cycle.status} /></td>
              <td>
                <div>{formatDateTime(cycle.start)}</div>
                <div class="muted">{formatDateTime(cycle.end)}</div>
              </td>
              <td>{formatList(cycle.symbols)}</td>
              <td>
                <div class="mono">A: {compactId(cycle.active_model_version)}</div>
                <div class="mono muted">C: {compactId(cycle.challenger_model_version)}</div>
              </td>
              <td>
                <div class="row-actions">
                  <button class="btn" onclick={() => dryRun(cycle.research_cycle_id)}>
                    <FlaskIcon size={16} />
                    Dry-run
                  </button>
                  <button class="btn" onclick={() => runCycle(cycle.research_cycle_id)}>
                    <PlayIcon size={16} />
                    Run
                  </button>
                  <button class="btn" onclick={() => exportCycle(cycle.research_cycle_id)}>
                    <FileArrowDownIcon size={16} />
                    Export
                  </button>
                </div>
              </td>
            </tr>
          {:else}
            <tr>
              <td colspan="6" class="muted">No research cycles returned by the backend.</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  {#if lastResult}
    <section class="panel">
      <JsonPanel title="Latest action response" value={lastResult} />
    </section>
  {/if}
</div>

<style>
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
  }

  h1,
  p {
    margin: 0;
  }

  p {
    color: var(--muted);
  }

  .form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 14px;
  }

  .wide {
    grid-column: span 2;
  }

  .checks,
  .row-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: center;
  }

  .checks {
    min-height: 38px;
    color: var(--text);
  }

  @media (max-width: 760px) {
    .wide {
      grid-column: span 1;
    }
  }
</style>
