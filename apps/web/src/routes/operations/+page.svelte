<script lang="ts">
  import { onMount } from 'svelte';
  import ArrowClockwiseIcon from 'phosphor-svelte/lib/ArrowClockwiseIcon';
  import DatabaseIcon from 'phosphor-svelte/lib/DatabaseIcon';
  import PulseIcon from 'phosphor-svelte/lib/PulseIcon';
  import ShieldCheckIcon from 'phosphor-svelte/lib/ShieldCheckIcon';
  import JsonPanel from '$lib/components/JsonPanel.svelte';
  import StatusBadge from '$lib/components/StatusBadge.svelte';
  import { fetchConfig, getHealth, getResearchStatus } from '$lib/api';
  import { compactId, formatDateTime } from '$lib/governance';
  import type { AppConfig, HealthStatus, ResearchStatus } from '$lib/types';

  let health = $state<HealthStatus>({ status: 'loading' });
  let config = $state<AppConfig | null>(null);
  let research = $state<ResearchStatus>({ status: 'loading' });
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
    const [nextHealth, nextConfig, nextResearch] = await Promise.all([
      getHealth(),
      fetchConfig(),
      getResearchStatus(),
    ]);
    health = nextHealth;
    config = nextConfig;
    research = nextResearch;
    loading = false;
  }

  onMount(() => {
    void refresh();
  });
</script>

<svelte:head>
  <title>Operations | Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <PulseIcon size={28} weight="duotone" />
    <div>
      <h1>Operations</h1>
      <p>Research governance status, persistence health, and scanner model readiness.</p>
    </div>
    <button class="btn" onclick={refresh} disabled={loading}>
      <ArrowClockwiseIcon size={18} />
      Refresh
    </button>
  </header>

  <section class="panel notice">
    <ShieldCheckIcon size={22} weight="duotone" />
    <div>
      <strong>No broker execution</strong>
      <span>Operations controls are status and research governance only.</span>
    </div>
  </section>

  <section class="grid">
    <div class="panel metric">
      <span>Backend</span>
      <StatusBadge value={health.status ?? 'unknown'} />
      <small>{formatDateTime(health.time)}</small>
    </div>
    <div class="panel metric">
      <span>Persistence</span>
      <strong>{field(health.persistence, 'backend', field(health.persistence, 'dialect'))}</strong>
      <small>{field(health.persistence, 'database_reachable', 'unknown')}</small>
    </div>
    <div class="panel metric">
      <span>Active model</span>
      <strong class="mono">{research.active_model_version ?? '-'}</strong>
      <small>{research.active_model_review_status ?? 'No current review status'}</small>
    </div>
    <div class="panel metric">
      <span>Provider config</span>
      <strong>{config?.fmp_api_key_configured ? 'Configured' : 'Missing'}</strong>
      <small>{config?.timezone ?? 'America/New_York'}</small>
    </div>
  </section>

  <section class="grid">
    <div class="panel metric">
      <span>Latest cycle</span>
      {#if research.latest_research_cycle}
        <a
          class="link mono"
          href={`/research/cycles/${research.latest_research_cycle.research_cycle_id}`}
        >
          {compactId(research.latest_research_cycle.research_cycle_id)}
        </a>
        <StatusBadge value={research.latest_research_cycle.status} />
      {:else}
        <strong>-</strong>
        <small>No recorded cycle</small>
      {/if}
    </div>
    <div class="panel metric">
      <span>Latest proposal</span>
      {#if research.latest_model_proposal}
        <a
          class="link mono"
          href={`/research/proposals/${research.latest_model_proposal.proposal_id}`}
        >
          {compactId(research.latest_model_proposal.proposal_id)}
        </a>
        <StatusBadge value={research.latest_model_proposal.status} />
      {:else}
        <strong>-</strong>
        <small>No recorded proposal</small>
      {/if}
    </div>
    <div class="panel metric">
      <span>Calibration drift</span>
      <StatusBadge value={research.latest_calibration_drift_severity ?? 'not reported'} />
      <small>Latest active-model drift severity</small>
    </div>
    <div class="panel metric">
      <span>Proposal queue</span>
      <strong>{research.pending_proposals?.length ?? 0} pending</strong>
      <small>{research.blocked_proposals?.length ?? 0} blocked</small>
    </div>
  </section>

  <section class="panel status-grid">
    <div>
      <h2>Stale windows</h2>
      <p>{field(research.stale_windows_summary, 'status', 'unknown')}</p>
      <p class="muted">
        Dirty windows: {field(research.stale_windows_summary, 'dirty_window_count', '0')}
      </p>
    </div>
    <div>
      <h2>Data quality</h2>
      <p>{field(research.data_quality_summary, 'status', 'unknown')}</p>
      <p class="muted">
        Invalid price/volume: {field(
          research.data_quality_summary,
          'invalid_price_or_volume_count',
          '0',
        )}
      </p>
    </div>
  </section>

  {#if research.warnings?.length}
    <section class="panel">
      <h2>Warnings</h2>
      <ul>
        {#each research.warnings as warning}
          <li>{warning}</li>
        {/each}
      </ul>
    </section>
  {/if}

  <section class="panel">
    <div class="section-title">
      <DatabaseIcon size={20} weight="duotone" />
      <h2>Backend payloads</h2>
    </div>
    <JsonPanel title="Research status payload" value={research} />
    <JsonPanel title="Health payload" value={health} />
  </section>
</div>

<style>
  header,
  .notice,
  .section-title {
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

  .metric strong,
  .notice strong {
    display: block;
  }

  .status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 18px;
  }

  .section-title {
    margin-bottom: 12px;
  }

  ul {
    padding-left: 18px;
  }
</style>
