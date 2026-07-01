<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import ArrowClockwiseIcon from 'phosphor-svelte/lib/ArrowClockwiseIcon';
  import FileArrowDownIcon from 'phosphor-svelte/lib/FileArrowDownIcon';
  import FlaskIcon from 'phosphor-svelte/lib/FlaskIcon';
  import PlayIcon from 'phosphor-svelte/lib/PlayIcon';
  import JsonPanel from '$lib/components/JsonPanel.svelte';
  import StatusBadge from '$lib/components/StatusBadge.svelte';
  import {
    dryRunResearchCycle,
    exportResearchCycle,
    getResearchCycle,
    getResearchCycleArtifacts,
    runResearchCycle,
    triggerExport,
  } from '$lib/api';
  import {
    compactId,
    formatDateTime,
    formatList,
    isApiFailure,
    prettyJson,
    safeExportSummary,
  } from '$lib/governance';
  import type { ResearchCycle, ResearchCycleArtifact } from '$lib/types';

  const cycleId = $derived(page.params.id ?? '');

  let cycle = $state<ResearchCycle | null>(null);
  let artifacts = $state<ResearchCycleArtifact[]>([]);
  let message = $state('No cycle action requested.');
  let lastResult = $state<unknown>(null);
  let loading = $state(false);
  let allowStale = $state(false);
  let refreshData = $state(false);

  function record(value: unknown): Record<string, unknown> {
    return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
  }

  function field(value: unknown, key: string, fallback = '-'): string {
    const item = record(value)[key];
    return item === null || item === undefined || item === '' ? fallback : String(item);
  }

  async function refresh() {
    loading = true;
    const [cycleResult, artifactResult] = await Promise.all([
      getResearchCycle(cycleId),
      getResearchCycleArtifacts(cycleId),
    ]);
    if (isApiFailure(cycleResult)) {
      message = `Cycle lookup failed: ${cycleResult.reason}`;
    } else {
      cycle = cycleResult;
    }
    artifacts = artifactResult.artifacts;
    loading = false;
  }

  async function dryRun() {
    const result = await dryRunResearchCycle(cycleId);
    lastResult = result;
    message = isApiFailure(result) ? `Dry-run failed: ${result.reason}` : 'Dry-run completed.';
  }

  async function runCycle() {
    const result = await runResearchCycle(cycleId, {
      allow_stale: allowStale,
      refresh_data: refreshData,
      export_reports: false,
    });
    lastResult = result;
    message = isApiFailure(result) ? `Run failed: ${result.reason}` : 'Run response received.';
    await refresh();
  }

  async function exportDefault() {
    const result = await exportResearchCycle(cycleId);
    lastResult = safeExportSummary(result);
    message = isApiFailure(result)
      ? `Export failed: ${result.reason}`
      : 'Research cycle export metadata received.';
  }

  async function exportKind(kind: 'research-cycle-xlsx' | 'research-cycle-json') {
    const result = await triggerExport(kind, cycleId);
    lastResult = safeExportSummary(result);
    message = result.status === 'error' ? 'Export failed.' : `${kind} export metadata received.`;
  }

  onMount(() => {
    void refresh();
  });
</script>

<svelte:head>
  <title>Research Cycle Detail | Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <FlaskIcon size={28} weight="duotone" />
    <div>
      <h1>Research cycle</h1>
      <p class="mono">{cycleId}</p>
    </div>
    <button class="btn" onclick={refresh} disabled={loading}>
      <ArrowClockwiseIcon size={18} />
      Refresh
    </button>
  </header>

  {#if cycle}
    <section class="grid">
      <div class="panel metric">
        <span>Status</span>
        <StatusBadge value={cycle.status} />
        <small>{formatDateTime(cycle.created_at)}</small>
      </div>
      <div class="panel metric">
        <span>Config hash</span>
        <strong class="mono">{compactId(cycle.config_hash)}</strong>
        <small>Input: {compactId(cycle.input_fingerprint)}</small>
      </div>
      <div class="panel metric">
        <span>Models</span>
        <strong class="mono">A: {compactId(cycle.active_model_version)}</strong>
        <small>C: {compactId(cycle.challenger_model_version)}</small>
      </div>
      <div class="panel metric">
        <span>Activation</span>
        <StatusBadge value={field(cycle.summary, 'model_activation_unchanged', 'true')} />
        <small>Cycle run does not activate models.</small>
      </div>
    </section>

    <section class="panel detail-grid">
      <div>
        <h2>Window</h2>
        <p>{formatDateTime(cycle.start)} to {formatDateTime(cycle.end)}</p>
        <p class="muted">Session: {cycle.session ?? 'rth'}</p>
      </div>
      <div>
        <h2>Inputs</h2>
        <p>{formatList(cycle.symbols)}</p>
        <p class="muted">{formatList(cycle.intervals)}</p>
      </div>
      <div>
        <h2>Data quality</h2>
        <p>
          {field(
            cycle.summary,
            'data_quality_status',
            field(cycle.stale_window_status, 'status', 'unknown'),
          )}
        </p>
        <p class="muted">
          Dirty windows: {field(cycle.stale_window_status, 'dirty_window_count', '0')}
        </p>
      </div>
    </section>

    <section class="panel toolbar">
      <label><input type="checkbox" bind:checked={allowStale} /> Allow stale</label>
      <label><input type="checkbox" bind:checked={refreshData} /> Refresh data</label>
      <button class="btn" onclick={dryRun}>
        <FlaskIcon size={18} />
        Dry-run
      </button>
      <button class="btn" onclick={runCycle}>
        <PlayIcon size={18} />
        Run
      </button>
      <button class="btn" onclick={exportDefault}>
        <FileArrowDownIcon size={18} />
        Export
      </button>
      <button class="btn" onclick={() => exportKind('research-cycle-xlsx')}>
        <FileArrowDownIcon size={18} />
        XLSX
      </button>
      <button class="btn" onclick={() => exportKind('research-cycle-json')}>
        <FileArrowDownIcon size={18} />
        JSON
      </button>
      <span class="muted">{message}</span>
    </section>

    {#if cycle.warnings?.length}
      <section class="panel">
        <h2>Warnings</h2>
        <ul>
          {#each cycle.warnings as warning}
            <li>{warning}</li>
          {/each}
        </ul>
      </section>
    {/if}

    <section class="panel">
      <h2>Artifacts</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Artifact</th>
              <th>Type</th>
              <th>Source</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {#each artifacts as artifact}
              <tr>
                <td class="mono">{compactId(artifact.cycle_artifact_id ?? artifact.artifact_id)}</td
                >
                <td>{artifact.artifact_type ?? '-'}</td>
                <td>
                  <div>{artifact.source_table ?? '-'}</div>
                  <div class="mono muted">{compactId(artifact.source_id)}</div>
                </td>
                <td>{formatDateTime(artifact.created_at)}</td>
              </tr>
            {:else}
              <tr>
                <td colspan="4" class="muted">No artifacts returned for this cycle.</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <JsonPanel title="Cycle summary" value={cycle.summary ?? cycle} />
      <JsonPanel title="Stale window status" value={cycle.stale_window_status ?? {}} />
      <JsonPanel title="Cycle config" value={cycle.config ?? {}} />
    </section>
  {:else}
    <section class="panel">
      <p>{message}</p>
    </section>
  {/if}

  {#if lastResult}
    <section class="panel">
      <JsonPanel title="Latest action response" value={lastResult} />
    </section>
  {/if}

  <section class="panel">
    <h2>Raw artifact payload preview</h2>
    <pre>{prettyJson(artifacts.slice(0, 3))}</pre>
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

  h1,
  h2,
  p,
  ul {
    margin: 0;
  }

  p,
  small,
  li,
  span,
  label {
    color: var(--muted);
  }

  .metric {
    display: grid;
    gap: 8px;
    min-height: 116px;
    align-content: start;
  }

  .detail-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 18px;
  }

  ul {
    padding-left: 18px;
  }

  pre {
    max-height: 260px;
    overflow: auto;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: #0c131a;
    color: #cfe3f3;
    padding: 12px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
</style>
