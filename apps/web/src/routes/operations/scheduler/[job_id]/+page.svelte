<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import ArrowClockwiseIcon from 'phosphor-svelte/lib/ArrowClockwiseIcon';
  import ClockCountdownIcon from 'phosphor-svelte/lib/ClockCountdownIcon';
  import PlayIcon from 'phosphor-svelte/lib/PlayIcon';
  import ProhibitIcon from 'phosphor-svelte/lib/ProhibitIcon';
  import JsonPanel from '$lib/components/JsonPanel.svelte';
  import StatusBadge from '$lib/components/StatusBadge.svelte';
  import {
    cancelSchedulerJob,
    getSchedulerJob,
    getSchedulerJobEvents,
    runSchedulerJob,
  } from '$lib/api';
  import { compactId, formatDateTime, isApiFailure } from '$lib/governance';
  import type { SchedulerJob, SchedulerJobEvent } from '$lib/types';

  const jobId = $derived(page.params.job_id ?? '');

  let job = $state<SchedulerJob | null>(null);
  let events = $state<SchedulerJobEvent[]>([]);
  let loading = $state(false);
  let message = $state('No scheduler action requested.');
  let lastResult = $state<unknown>(null);

  async function refresh() {
    loading = true;
    const [jobResult, eventResult] = await Promise.all([
      getSchedulerJob(jobId),
      getSchedulerJobEvents(jobId),
    ]);
    if (isApiFailure(jobResult)) {
      message = `Job lookup failed: ${jobResult.reason}`;
    } else {
      job = jobResult;
    }
    events = eventResult.events;
    loading = false;
  }

  async function runJob() {
    const result = await runSchedulerJob(jobId);
    lastResult = result;
    message = isApiFailure(result) ? `Run failed: ${result.reason}` : 'Run response received.';
    await refresh();
  }

  async function cancelJob() {
    const result = await cancelSchedulerJob(jobId);
    lastResult = result;
    message = isApiFailure(result)
      ? `Cancel failed: ${result.reason}`
      : 'Cancel response received.';
    await refresh();
  }

  onMount(() => {
    void refresh();
  });
</script>

<svelte:head>
  <title>Scheduler Job | Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <ClockCountdownIcon size={28} weight="duotone" />
    <div>
      <h1>Scheduler job</h1>
      <p class="mono">{jobId}</p>
    </div>
    <button class="btn" onclick={refresh} disabled={loading}>
      <ArrowClockwiseIcon size={18} />
      Refresh
    </button>
  </header>

  {#if job}
    <section class="grid">
      <div class="panel metric">
        <span>Status</span>
        <StatusBadge value={job.status} />
        <small>{formatDateTime(job.updated_at)}</small>
      </div>
      <div class="panel metric">
        <span>Type</span>
        <strong>{job.job_type}</strong>
        <small>Priority {job.priority ?? 100}</small>
      </div>
      <div class="panel metric">
        <span>Research cycle</span>
        {#if job.research_cycle_id}
          <a class="link mono" href={`/research/cycles/${job.research_cycle_id}`}>
            {compactId(job.research_cycle_id)}
          </a>
        {:else}
          <strong>-</strong>
        {/if}
        <small>{job.created_by ?? 'local operator'}</small>
      </div>
      <div class="panel metric">
        <span>Failure reason</span>
        <strong>{job.failed_reason ?? '-'}</strong>
        <small>{formatDateTime(job.completed_at)}</small>
      </div>
    </section>

    <section class="panel toolbar">
      <button class="btn" onclick={runJob} disabled={job.status !== 'QUEUED'}>
        <PlayIcon size={16} />
        Run job
      </button>
      <button class="btn" onclick={cancelJob} disabled={job.status !== 'QUEUED'}>
        <ProhibitIcon size={16} />
        Cancel job
      </button>
      <span class="muted">{message}</span>
    </section>

    {#if job.warnings?.length}
      <section class="panel">
        <h2>Warnings</h2>
        <ul>
          {#each job.warnings as warning}
            <li>{warning}</li>
          {/each}
        </ul>
      </section>
    {/if}

    <section class="panel">
      <h2>Events</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Type</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {#each events as event}
              <tr>
                <td>{formatDateTime(event.created_at)}</td>
                <td>{event.event_type}</td>
                <td>{event.message}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <JsonPanel title="Payload" value={job.payload ?? {}} />
      <JsonPanel title="Result" value={job.result ?? {}} />
      <JsonPanel title="Last action response" value={lastResult} />
    </section>
  {:else}
    <section class="panel">
      <p>{message}</p>
    </section>
  {/if}
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
  h2,
  p,
  ul {
    margin: 0;
  }

  p,
  small,
  span,
  li,
  .muted {
    color: var(--muted);
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
