<script lang="ts">
  import { onMount } from 'svelte';
  import ArrowClockwiseIcon from 'phosphor-svelte/lib/ArrowClockwiseIcon';
  import PulseIcon from 'phosphor-svelte/lib/PulseIcon';
  import JsonPanel from '$lib/components/JsonPanel.svelte';
  import StatusBadge from '$lib/components/StatusBadge.svelte';
  import { getResearchStatus } from '$lib/api';
  import { compactId, formatDateTime } from '$lib/governance';
  import type { ResearchStatus } from '$lib/types';

  let status = $state<ResearchStatus>({ status: 'loading' });
  let loading = $state(false);

  function record(value: unknown): Record<string, unknown> {
    return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
  }

  function field(value: unknown, key: string, fallback = '-'): string {
    const item = record(value)[key];
    return item === null || item === undefined || item === '' ? fallback : String(item);
  }

  async function refresh() {
    loading = true;
    status = await getResearchStatus();
    loading = false;
  }

  onMount(() => {
    void refresh();
  });
</script>

<svelte:head>
  <title>Research Status | Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <PulseIcon size={28} weight="duotone" />
    <div>
      <h1>Research status</h1>
      <p>
        Read-only governance status for active model, cycles, proposals, stale windows, and data
        quality.
      </p>
    </div>
    <button class="btn" onclick={refresh} disabled={loading}>
      <ArrowClockwiseIcon size={18} />
      Refresh
    </button>
  </header>

  <section class="grid">
    <div class="panel metric">
      <span>Research API</span>
      <StatusBadge value={status.status} />
      <small>Operations research status endpoint</small>
    </div>
    <div class="panel metric">
      <span>Active model</span>
      <strong class="mono">{status.active_model_version ?? '-'}</strong>
      <small>{status.active_model_review_status ?? 'No active review status'}</small>
    </div>
    <div class="panel metric">
      <span>Calibration drift</span>
      <StatusBadge value={status.latest_calibration_drift_severity ?? 'not reported'} />
      <small>Latest active-model drift severity</small>
    </div>
    <div class="panel metric">
      <span>Proposal queue</span>
      <strong>{status.pending_proposals?.length ?? 0} pending</strong>
      <small>{status.blocked_proposals?.length ?? 0} blocked</small>
    </div>
  </section>

  <section class="grid">
    <div class="panel metric">
      <span>Latest cycle</span>
      {#if status.latest_research_cycle}
        <a
          class="link mono"
          href={`/research/cycles/${status.latest_research_cycle.research_cycle_id}`}
        >
          {compactId(status.latest_research_cycle.research_cycle_id)}
        </a>
        <StatusBadge value={status.latest_research_cycle.status} />
        <small
          >{formatDateTime(
            status.latest_research_cycle.completed_at ?? status.latest_research_cycle.created_at,
          )}</small
        >
      {:else}
        <strong>-</strong>
        <small>No latest cycle</small>
      {/if}
    </div>
    <div class="panel metric">
      <span>Latest proposal</span>
      {#if status.latest_model_proposal}
        <a
          class="link mono"
          href={`/research/proposals/${status.latest_model_proposal.proposal_id}`}
        >
          {compactId(status.latest_model_proposal.proposal_id)}
        </a>
        <StatusBadge value={status.latest_model_proposal.status} />
        <small
          >{formatDateTime(
            status.latest_model_proposal.updated_at ?? status.latest_model_proposal.created_at,
          )}</small
        >
      {:else}
        <strong>-</strong>
        <small>No latest proposal</small>
      {/if}
    </div>
    <div class="panel metric">
      <span>Stale windows</span>
      <StatusBadge value={field(status.stale_windows_summary, 'status', 'unknown')} />
      <small>Dirty: {field(status.stale_windows_summary, 'dirty_window_count', '0')}</small>
    </div>
    <div class="panel metric">
      <span>Data quality</span>
      <strong>{field(status.data_quality_summary, 'status', 'unknown')}</strong>
      <small
        >Invalid price/volume: {field(
          status.data_quality_summary,
          'invalid_price_or_volume_count',
          '0',
        )}</small
      >
    </div>
  </section>

  <section class="panel split">
    <div>
      <h2>Pending proposals</h2>
      {#each status.pending_proposals ?? [] as proposal}
        <p>
          <a class="link mono" href={`/research/proposals/${proposal.proposal_id}`}
            >{proposal.proposal_id}</a
          >
          <StatusBadge value={proposal.status} />
        </p>
      {:else}
        <p class="muted">No pending proposals.</p>
      {/each}
    </div>
    <div>
      <h2>Blocked proposals</h2>
      {#each status.blocked_proposals ?? [] as proposal}
        <p>
          <a class="link mono" href={`/research/proposals/${proposal.proposal_id}`}
            >{proposal.proposal_id}</a
          >
          <StatusBadge value={proposal.readiness_status ?? proposal.status} />
        </p>
      {:else}
        <p class="muted">No blocked proposals.</p>
      {/each}
    </div>
  </section>

  {#if status.warnings?.length}
    <section class="panel">
      <h2>Warnings</h2>
      <ul>
        {#each status.warnings as warning}
          <li>{warning}</li>
        {/each}
      </ul>
    </section>
  {/if}

  <section class="panel">
    <JsonPanel title="Research status payload" value={status} />
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
  span {
    color: var(--muted);
  }

  .metric {
    display: grid;
    gap: 8px;
    min-height: 116px;
    align-content: start;
  }

  .split {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 18px;
  }

  .split p {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    margin-top: 8px;
  }

  ul {
    padding-left: 18px;
  }
</style>
