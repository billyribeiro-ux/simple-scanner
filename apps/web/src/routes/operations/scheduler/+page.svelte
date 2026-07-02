<script lang="ts">
  import { onMount } from 'svelte';
  import ArrowClockwiseIcon from 'phosphor-svelte/lib/ArrowClockwiseIcon';
  import ClockCountdownIcon from 'phosphor-svelte/lib/ClockCountdownIcon';
  import ListChecksIcon from 'phosphor-svelte/lib/ListChecksIcon';
  import PlayIcon from 'phosphor-svelte/lib/PlayIcon';
  import ProhibitIcon from 'phosphor-svelte/lib/ProhibitIcon';
  import JsonPanel from '$lib/components/JsonPanel.svelte';
  import StatusBadge from '$lib/components/StatusBadge.svelte';
  import {
    cancelSchedulerJob,
    createSchedulerJob,
    getSchedulerStatus,
    listSchedulerJobs,
    runPendingSchedulerJobs,
    runSchedulerJob,
    type SchedulerJobCreatePayload,
  } from '$lib/api';
  import { compactId, formatDateTime, isApiFailure, normalizeSymbolsInput } from '$lib/governance';
  import type { SchedulerJob, SchedulerStatus } from '$lib/types';

  type SchedulerJobType = SchedulerJobCreatePayload['job_type'];

  let jobs = $state<SchedulerJob[]>([]);
  let scheduler = $state<SchedulerStatus>({ status: 'loading' });
  let loading = $state(false);
  let interactiveReady = $state(false);
  let statusFilter = $state('');
  let message = $state('No scheduler action requested.');
  let lastResult = $state<unknown>(null);

  let jobType = $state<SchedulerJobType>('data_quality_report');
  let researchCycleId = $state('');
  let symbols = $state('AAPL,SPY');
  let intervals = $state('1min');
  let maxJobs = $state(3);
  let allowStale = $state(false);
  let refreshData = $state(false);
  let exportKind = $state('xlsx');

  function intervalList(): string[] {
    return intervals
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean);
  }

  function jobPayload(): SchedulerJobCreatePayload {
    const selectedSymbols = normalizeSymbolsInput(symbols);
    if (jobType === 'data_quality_report') {
      return {
        job_type: jobType,
        payload: { symbols: selectedSymbols, intervals: intervalList(), session: 'rth' },
        created_by: 'operator-ui',
      };
    }
    if (jobType === 'export_operations_status') {
      return { job_type: jobType, payload: {}, created_by: 'operator-ui' };
    }
    if (jobType === 'export_research_cycle') {
      return {
        job_type: jobType,
        payload: { research_cycle_id: researchCycleId, kind: exportKind },
        created_by: 'operator-ui',
      };
    }
    const cyclePayload = researchCycleId
      ? { research_cycle_id: researchCycleId, allow_stale: allowStale, refresh_data: refreshData }
      : {
          research_cycle: {
            cycle_type: 'daily',
            symbols: selectedSymbols,
            intervals: intervalList(),
            session: 'rth',
            allow_stale: allowStale,
            refresh_data: refreshData,
            run_now: false,
          },
          run: { allow_stale: allowStale, refresh_data: refreshData },
        };
    return { job_type: jobType, payload: cyclePayload, created_by: 'operator-ui' };
  }

  async function refresh() {
    loading = true;
    const [nextStatus, nextJobs] = await Promise.all([
      getSchedulerStatus(),
      listSchedulerJobs({ status: statusFilter || undefined }),
    ]);
    scheduler = nextStatus;
    jobs = nextJobs.jobs;
    loading = false;
  }

  async function createJob() {
    const result = await createSchedulerJob(jobPayload());
    lastResult = result;
    message = isApiFailure(result)
      ? `Job create failed: ${result.reason}`
      : `Queued job ${result.job_id}`;
    await refresh();
  }

  async function runJob(jobId: string) {
    const result = await runSchedulerJob(jobId);
    lastResult = result;
    message = isApiFailure(result) ? `Run failed: ${result.reason}` : `Run completed for ${jobId}`;
    await refresh();
  }

  async function cancelJob(jobId: string) {
    const result = await cancelSchedulerJob(jobId);
    lastResult = result;
    message = isApiFailure(result)
      ? `Cancel failed: ${result.reason}`
      : `Cancel response received for ${jobId}`;
    await refresh();
  }

  async function runPending() {
    const result = await runPendingSchedulerJobs(maxJobs);
    lastResult = result;
    const count = typeof result.jobs_run === 'number' ? result.jobs_run : 0;
    message = `Run pending completed: ${count} jobs`;
    await refresh();
  }

  onMount(() => {
    interactiveReady = true;
    void refresh();
  });
</script>

<svelte:head>
  <title>Scheduler | Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <ClockCountdownIcon size={28} weight="duotone" />
    <div>
      <h1>Scheduler</h1>
      <p>Bounded research preparation queue and persisted job events.</p>
    </div>
    <button class="btn" onclick={refresh} disabled={!interactiveReady || loading}>
      <ArrowClockwiseIcon size={18} />
      Refresh
    </button>
  </header>

  <section class="grid">
    <div class="panel metric">
      <span>Queued</span>
      <strong>{scheduler.queued_jobs ?? 0}</strong>
      <small>{scheduler.running_jobs ?? 0} running</small>
    </div>
    <div class="panel metric">
      <span>Completed</span>
      <strong>{scheduler.completed_jobs ?? 0}</strong>
      <small>{scheduler.cancelled_jobs ?? 0} cancelled</small>
    </div>
    <div class="panel metric">
      <span>Failed or blocked</span>
      <strong>{scheduler.failed_jobs ?? 0}</strong>
      {#if scheduler.latest_failed_job}
        <small>{compactId(scheduler.latest_failed_job.job_id)}</small>
      {:else}
        <small>None recorded</small>
      {/if}
    </div>
    <div class="panel metric">
      <span>Latest job</span>
      {#if scheduler.latest_job}
        <a class="link mono" href={`/operations/scheduler/${scheduler.latest_job.job_id}`}>
          {compactId(scheduler.latest_job.job_id)}
        </a>
        <StatusBadge value={scheduler.latest_job.status} />
      {:else}
        <strong>-</strong>
        <small>No jobs recorded</small>
      {/if}
    </div>
  </section>

  <section class="panel form-grid">
    <label class="field"
      >Job type
      <select bind:value={jobType}>
        <option value="data_quality_report">data_quality_report</option>
        <option value="research_cycle_dry_run">research_cycle_dry_run</option>
        <option value="research_cycle_run">research_cycle_run</option>
        <option value="export_research_cycle">export_research_cycle</option>
        <option value="export_operations_status">export_operations_status</option>
      </select>
    </label>
    <label class="field wide">Research cycle ID <input bind:value={researchCycleId} /></label>
    <label class="field">Symbols <input bind:value={symbols} /></label>
    <label class="field">Intervals <input bind:value={intervals} /></label>
    <label class="field"
      >Export kind
      <select bind:value={exportKind}>
        <option value="xlsx">xlsx</option>
        <option value="json">json</option>
      </select>
    </label>
    <div class="field">
      Run flags
      <div class="checks">
        <label><input type="checkbox" bind:checked={allowStale} /> Allow stale</label>
        <label><input type="checkbox" bind:checked={refreshData} /> Refresh data</label>
      </div>
    </div>
    <div class="toolbar">
      <button class="btn primary" onclick={createJob} disabled={!interactiveReady}>
        <ListChecksIcon size={16} />
        Create job
      </button>
    </div>
  </section>

  <section class="panel toolbar">
    <label class="field"
      >Status filter
      <select bind:value={statusFilter} onchange={refresh}>
        <option value="">All</option>
        <option value="QUEUED">QUEUED</option>
        <option value="RUNNING">RUNNING</option>
        <option value="COMPLETED">COMPLETED</option>
        <option value="BLOCKED">BLOCKED</option>
        <option value="FAILED">FAILED</option>
        <option value="CANCELLED">CANCELLED</option>
      </select>
    </label>
    <label class="field compact"
      >Max jobs <input type="number" min="1" max="10" bind:value={maxJobs} /></label
    >
    <button class="btn" onclick={runPending} disabled={!interactiveReady}>
      <PlayIcon size={16} />
      Run pending
    </button>
    <span class="muted">{message}</span>
  </section>

  <section class="panel">
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Job</th>
            <th>Type</th>
            <th>Status</th>
            <th>Cycle</th>
            <th>Updated</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each jobs as job}
            <tr>
              <td>
                <a class="link mono" href={`/operations/scheduler/${job.job_id}`}>
                  {compactId(job.job_id)}
                </a>
                <div class="muted">{formatDateTime(job.created_at)}</div>
              </td>
              <td>{job.job_type}</td>
              <td><StatusBadge value={job.status} /></td>
              <td class="mono">{compactId(job.research_cycle_id)}</td>
              <td>{formatDateTime(job.updated_at)}</td>
              <td>
                <div class="row-actions">
                  <button
                    class="btn"
                    onclick={() => runJob(job.job_id)}
                    disabled={job.status !== 'QUEUED'}
                  >
                    <PlayIcon size={16} />
                    Run
                  </button>
                  <button
                    class="btn"
                    onclick={() => cancelJob(job.job_id)}
                    disabled={job.status !== 'QUEUED'}
                  >
                    <ProhibitIcon size={16} />
                    Cancel
                  </button>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section class="panel">
    <JsonPanel title="Last scheduler response" value={lastResult} />
  </section>
</div>

<style>
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
  }

  header > div {
    flex: 1;
    min-width: 260px;
  }

  h1,
  p {
    margin: 0;
  }

  p,
  small,
  span,
  .muted {
    color: var(--muted);
  }

  .metric {
    display: grid;
    gap: 8px;
    min-height: 116px;
    align-content: start;
  }

  .compact {
    max-width: 120px;
  }
</style>
