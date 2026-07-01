<script lang="ts">
  import { onMount } from 'svelte';
  import ArrowClockwiseIcon from 'phosphor-svelte/lib/ArrowClockwiseIcon';
  import ClipboardTextIcon from 'phosphor-svelte/lib/ClipboardTextIcon';
  import FileArrowDownIcon from 'phosphor-svelte/lib/FileArrowDownIcon';
  import JsonPanel from '$lib/components/JsonPanel.svelte';
  import StatusBadge from '$lib/components/StatusBadge.svelte';
  import { listModelProposals, triggerExport } from '$lib/api';
  import { compactId, formatDateTime, safeExportSummary } from '$lib/governance';
  import type { ModelProposal } from '$lib/types';

  let proposals = $state<ModelProposal[]>([]);
  let statusFilter = $state('');
  let loading = $state(false);
  let message = $state('No proposal action requested.');
  let lastResult = $state<unknown>(null);

  async function refresh() {
    loading = true;
    const payload = await listModelProposals({ status: statusFilter || undefined });
    proposals = payload.model_proposals;
    loading = false;
  }

  async function exportProposal(proposalId: string) {
    const result = await triggerExport('model-proposal-xlsx', proposalId);
    lastResult = safeExportSummary(result);
    message =
      result.status === 'error' ? 'Export failed.' : `Export metadata received for ${proposalId}`;
  }

  onMount(() => {
    void refresh();
  });
</script>

<svelte:head>
  <title>Model Proposals | Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <ClipboardTextIcon size={28} weight="duotone" />
    <div>
      <h1>Model proposals</h1>
      <p>Human review surface for champion/challenger evidence and backend readiness gates.</p>
    </div>
    <button class="btn" onclick={refresh} disabled={loading}>
      <ArrowClockwiseIcon size={18} />
      Refresh
    </button>
  </header>

  <section class="panel toolbar">
    <label class="field"
      >Status filter
      <select bind:value={statusFilter} onchange={refresh}>
        <option value="">All</option>
        <option value="PROPOSED">PROPOSED</option>
        <option value="APPROVED_FOR_ACTIVATION">APPROVED_FOR_ACTIVATION</option>
        <option value="ACTIVATED">ACTIVATED</option>
        <option value="REJECTED">REJECTED</option>
      </select>
    </label>
    <span class="muted">{message}</span>
  </section>

  <section class="panel">
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Proposal</th>
            <th>Status</th>
            <th>Readiness</th>
            <th>Recommendation</th>
            <th>Models</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each proposals as proposal}
            <tr>
              <td>
                <a class="link mono" href={`/research/proposals/${proposal.proposal_id}`}>
                  {compactId(proposal.proposal_id)}
                </a>
                {#if proposal.research_cycle_id}
                  <div>
                    <a class="link mono" href={`/research/cycles/${proposal.research_cycle_id}`}>
                      cycle {compactId(proposal.research_cycle_id)}
                    </a>
                  </div>
                {/if}
              </td>
              <td><StatusBadge value={proposal.status} /></td>
              <td><StatusBadge value={proposal.readiness_status ?? 'unknown'} /></td>
              <td>{proposal.recommended_action ?? '-'}</td>
              <td>
                <div class="mono">A: {compactId(proposal.champion_model_version)}</div>
                <div class="mono muted">C: {compactId(proposal.challenger_model_version)}</div>
              </td>
              <td>{formatDateTime(proposal.created_at)}</td>
              <td>
                <div class="row-actions">
                  <a class="btn" href={`/research/proposals/${proposal.proposal_id}`}>Review</a>
                  <button class="btn" onclick={() => exportProposal(proposal.proposal_id)}>
                    <FileArrowDownIcon size={16} />
                    Export
                  </button>
                </div>
              </td>
            </tr>
          {:else}
            <tr>
              <td colspan="7" class="muted">No model proposals returned by the backend.</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  {#if lastResult}
    <section class="panel">
      <JsonPanel title="Latest export response" value={lastResult} />
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

  .row-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
</style>
