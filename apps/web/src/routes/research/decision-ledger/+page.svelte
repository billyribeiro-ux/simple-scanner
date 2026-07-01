<script lang="ts">
  import { onMount } from 'svelte';
  import ArrowClockwiseIcon from 'phosphor-svelte/lib/ArrowClockwiseIcon';
  import ListChecksIcon from 'phosphor-svelte/lib/ListChecksIcon';
  import JsonPanel from '$lib/components/JsonPanel.svelte';
  import StatusBadge from '$lib/components/StatusBadge.svelte';
  import { listDecisionLedger } from '$lib/api';
  import { compactId, formatDateTime, formatList } from '$lib/governance';
  import type { DecisionLedgerEvent } from '$lib/types';

  let decisions = $state<DecisionLedgerEvent[]>([]);
  let modelVersion = $state('');
  let proposalId = $state('');
  let researchCycleId = $state('');
  let decisionType = $state('');
  let start = $state('');
  let end = $state('');
  let loading = $state(false);
  let message = $state('No filters applied.');

  function optionalDateTime(value: string): string | undefined {
    return value ? new Date(value).toISOString() : undefined;
  }

  async function refresh() {
    loading = true;
    const payload = await listDecisionLedger({
      model_version: modelVersion || undefined,
      proposal_id: proposalId || undefined,
      research_cycle_id: researchCycleId || undefined,
      decision_type: decisionType || undefined,
      start: optionalDateTime(start),
      end: optionalDateTime(end),
    });
    decisions = payload.decisions;
    message = `${payload.decisions.length} decisions returned.`;
    loading = false;
  }

  function clearFilters() {
    modelVersion = '';
    proposalId = '';
    researchCycleId = '';
    decisionType = '';
    start = '';
    end = '';
    void refresh();
  }

  onMount(() => {
    void refresh();
  });
</script>

<svelte:head>
  <title>Decision Ledger | Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <ListChecksIcon size={28} weight="duotone" />
    <div>
      <h1>Decision ledger</h1>
      <p>
        Append-only governance record for cycles, proposals, approvals, blocked activations, and
        activations.
      </p>
    </div>
    <button class="btn" onclick={refresh} disabled={loading}>
      <ArrowClockwiseIcon size={18} />
      Refresh
    </button>
  </header>

  <section class="panel">
    <form
      class="form-grid"
      onsubmit={(event) => {
        event.preventDefault();
        void refresh();
      }}
    >
      <label class="field">Model version <input bind:value={modelVersion} /></label>
      <label class="field">Proposal ID <input bind:value={proposalId} /></label>
      <label class="field">Research cycle ID <input bind:value={researchCycleId} /></label>
      <label class="field">Decision type <input bind:value={decisionType} /></label>
      <label class="field">Start <input type="datetime-local" bind:value={start} /></label>
      <label class="field">End <input type="datetime-local" bind:value={end} /></label>
      <div class="toolbar">
        <button class="btn primary" type="submit">Apply filters</button>
        <button class="btn" type="button" onclick={clearFilters}>Clear</button>
        <span class="muted">{message}</span>
      </div>
    </form>
  </section>

  <section class="panel">
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Decision</th>
            <th>Status</th>
            <th>Actor</th>
            <th>Linked IDs</th>
            <th>Reasons</th>
            <th>Evidence</th>
            <th>Timestamp</th>
          </tr>
        </thead>
        <tbody>
          {#each decisions as decision}
            <tr>
              <td>{decision.decision_type}</td>
              <td><StatusBadge value={decision.decision_status ?? 'recorded'} /></td>
              <td>{decision.actor ?? '-'}</td>
              <td>
                {#if decision.proposal_id}
                  <a class="link mono" href={`/research/proposals/${decision.proposal_id}`}>
                    proposal {compactId(decision.proposal_id)}
                  </a>
                {/if}
                {#if decision.research_cycle_id}
                  <div>
                    <a class="link mono" href={`/research/cycles/${decision.research_cycle_id}`}>
                      cycle {compactId(decision.research_cycle_id)}
                    </a>
                  </div>
                {/if}
                {#if decision.model_version}
                  <div class="mono muted">model {compactId(decision.model_version)}</div>
                {/if}
              </td>
              <td>{formatList(decision.reason_codes)}</td>
              <td>
                <JsonPanel title="Evidence refs" value={decision.evidence_refs ?? []} />
              </td>
              <td>{formatDateTime(decision.created_at)}</td>
            </tr>
          {:else}
            <tr>
              <td colspan="7" class="muted">No ledger decisions returned by the backend.</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
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
  p {
    margin: 0;
  }

  p {
    color: var(--muted);
  }

  .form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 14px;
  }
</style>
