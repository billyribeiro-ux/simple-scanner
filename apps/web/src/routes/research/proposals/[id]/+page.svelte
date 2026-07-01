<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import ArrowClockwiseIcon from 'phosphor-svelte/lib/ArrowClockwiseIcon';
  import CheckCircleIcon from 'phosphor-svelte/lib/CheckCircleIcon';
  import FileArrowDownIcon from 'phosphor-svelte/lib/FileArrowDownIcon';
  import ShieldWarningIcon from 'phosphor-svelte/lib/ShieldWarningIcon';
  import XCircleIcon from 'phosphor-svelte/lib/XCircleIcon';
  import JsonPanel from '$lib/components/JsonPanel.svelte';
  import StatusBadge from '$lib/components/StatusBadge.svelte';
  import {
    activateModelProposal,
    approveModelProposal,
    getModelProposal,
    listDecisionLedger,
    rejectModelProposal,
    triggerExport,
  } from '$lib/api';
  import {
    ACTIVATION_CONFIRMATION_PHRASE,
    compactId,
    formatDateTime,
    formatList,
    isApiFailure,
    safeExportSummary,
  } from '$lib/governance';
  import type { DecisionLedgerEvent, ModelProposal } from '$lib/types';

  const proposalId = $derived(page.params.id ?? '');

  let proposal = $state<ModelProposal | null>(null);
  let decisions = $state<DecisionLedgerEvent[]>([]);
  let actor = $state('operator');
  let rejectionReasonCodes = $state('manual_rejection');
  let activationPhrase = $state('');
  let explicitConfirmation = $state(false);
  let validationMode = $state('replay_aware_walk_forward');
  let calibrationAuditRequired = $state(false);
  let loading = $state(false);
  let message = $state('No proposal action requested.');
  let lastResult = $state<unknown>(null);

  const activationReady = $derived(
    proposal?.status === 'APPROVED_FOR_ACTIVATION' &&
      explicitConfirmation &&
      activationPhrase === ACTIVATION_CONFIRMATION_PHRASE,
  );

  function record(value: unknown): Record<string, unknown> {
    return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
  }

  function metricEntries(value: unknown): Array<[string, unknown]> {
    return Object.entries(record(value)).slice(0, 10);
  }

  function reasonCodes(): string[] {
    return rejectionReasonCodes
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean);
  }

  async function refresh() {
    loading = true;
    const [proposalResult, ledgerResult] = await Promise.all([
      getModelProposal(proposalId),
      listDecisionLedger({ proposal_id: proposalId }),
    ]);
    if (isApiFailure(proposalResult)) {
      message = `Proposal lookup failed: ${proposalResult.reason}`;
    } else {
      proposal = proposalResult;
    }
    decisions = ledgerResult.decisions;
    loading = false;
  }

  async function approve() {
    const result = await approveModelProposal(proposalId, {
      actor,
      reason_codes: ['manual_operator_review'],
    });
    lastResult = result;
    if (isApiFailure(result)) {
      message = `Approval failed: ${result.reason}`;
      return;
    }
    proposal = result;
    message =
      'Proposal approved for activation review. Activation still requires explicit confirmation.';
    await refresh();
  }

  async function reject() {
    const result = await rejectModelProposal(proposalId, {
      actor,
      reason_codes: reasonCodes(),
    });
    lastResult = result;
    if (isApiFailure(result)) {
      message = `Rejection failed: ${result.reason}`;
      return;
    }
    proposal = result;
    message = 'Proposal rejected.';
    await refresh();
  }

  async function activate() {
    if (!activationReady) {
      message = 'Explicit confirmation is required before activation.';
      return;
    }
    const result = await activateModelProposal(proposalId, {
      actor,
      confirm_manual_activation: true,
      validation_mode: validationMode || undefined,
      calibration_audit_required: calibrationAuditRequired,
    });
    lastResult = result;
    message =
      result.status === 'ok'
        ? 'Activation response accepted by backend guard.'
        : `Activation response: ${result.reason ?? result.status}`;
    await refresh();
  }

  async function exportProposal(kind: 'model-proposal-xlsx' | 'model-proposal-json') {
    const result = await triggerExport(kind, proposalId);
    lastResult = safeExportSummary(result);
    message = result.status === 'error' ? 'Export failed.' : `${kind} export metadata received.`;
  }

  onMount(() => {
    void refresh();
  });
</script>

<svelte:head>
  <title>Model Proposal Detail | Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <ShieldWarningIcon size={28} weight="duotone" />
    <div>
      <h1>Model proposal</h1>
      <p class="mono">{proposalId}</p>
    </div>
    <button class="btn" onclick={refresh} disabled={loading}>
      <ArrowClockwiseIcon size={18} />
      Refresh
    </button>
  </header>

  {#if proposal}
    <section class="grid">
      <div class="panel metric">
        <span>Status</span>
        <StatusBadge value={proposal.status} />
        <small>{formatDateTime(proposal.updated_at ?? proposal.created_at)}</small>
      </div>
      <div class="panel metric">
        <span>Readiness</span>
        <StatusBadge value={proposal.readiness_status ?? 'unknown'} />
        <small>{proposal.recommended_action ?? 'No recommendation'}</small>
      </div>
      <div class="panel metric">
        <span>Champion</span>
        <strong class="mono">{compactId(proposal.champion_model_version)}</strong>
        <small>Current comparator</small>
      </div>
      <div class="panel metric">
        <span>Challenger</span>
        <strong class="mono">{compactId(proposal.challenger_model_version)}</strong>
        <small>Candidate scanner model</small>
      </div>
    </section>

    <section class="panel toolbar">
      <label class="field">Actor <input bind:value={actor} /></label>
      <button class="btn primary" onclick={approve}>
        <CheckCircleIcon size={18} />
        Approve proposal
      </button>
      <label class="field reject-field"
        >Reject reason codes <input bind:value={rejectionReasonCodes} /></label
      >
      <button class="btn danger" onclick={reject}>
        <XCircleIcon size={18} />
        Reject proposal
      </button>
      <button class="btn" onclick={() => exportProposal('model-proposal-xlsx')}>
        <FileArrowDownIcon size={18} />
        XLSX
      </button>
      <button class="btn" onclick={() => exportProposal('model-proposal-json')}>
        <FileArrowDownIcon size={18} />
        JSON
      </button>
    </section>

    <section class="panel danger-panel">
      <div class="activation-head">
        <ShieldWarningIcon size={24} weight="duotone" />
        <div>
          <h2>Explicit activation required</h2>
          <p>This changes scanner model only. It does not trade.</p>
        </div>
      </div>
      <div class="activation-grid">
        <label class="field"
          >Validation mode <input
            bind:value={validationMode}
            placeholder="optional backend mode"
          /></label
        >
        <label class="field"
          >Confirmation phrase
          <input
            bind:value={activationPhrase}
            aria-label="Activation confirmation phrase"
            placeholder={ACTIVATION_CONFIRMATION_PHRASE}
          /></label
        >
        <label class="check-row">
          <input type="checkbox" bind:checked={explicitConfirmation} />
          I understand this is a manual scanner model update only.
        </label>
        <label class="check-row">
          <input type="checkbox" bind:checked={calibrationAuditRequired} />
          Require calibration audit guard
        </label>
      </div>
      <button class="btn danger" onclick={activate} disabled={!activationReady}>
        <ShieldWarningIcon size={18} />
        Activate approved scanner model
      </button>
      <p class="muted">
        Required phrase: <span class="mono">{ACTIVATION_CONFIRMATION_PHRASE}</span>. Approving a
        proposal never triggers activation.
      </p>
    </section>

    <section class="panel detail-grid">
      <div>
        <h2>Evidence summary</h2>
        {#each metricEntries(proposal.evidence_summary) as [key, value]}
          <p><span>{key}</span> {String(value)}</p>
        {:else}
          <p class="muted">No evidence summary returned.</p>
        {/each}
      </div>
      <div>
        <h2>Pass/fail gates</h2>
        {#each metricEntries(proposal.pass_fail_gates) as [key, value]}
          <p><span>{key}</span> {String(value)}</p>
        {:else}
          <p class="muted">No gate summary returned.</p>
        {/each}
      </div>
      <div>
        <h2>Rejection reasons</h2>
        <p>{formatList(proposal.rejection_reasons)}</p>
      </div>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>Champion metrics</h2>
        {#each metricEntries(proposal.champion_metrics) as [key, value]}
          <p><span>{key}</span> {String(value)}</p>
        {:else}
          <p class="muted">No champion metrics returned.</p>
        {/each}
      </div>
      <div class="panel">
        <h2>Challenger metrics</h2>
        {#each metricEntries(proposal.challenger_metrics) as [key, value]}
          <p><span>{key}</span> {String(value)}</p>
        {:else}
          <p class="muted">No challenger metrics returned.</p>
        {/each}
      </div>
      <div class="panel">
        <h2>Delta metrics</h2>
        {#each metricEntries(proposal.delta_metrics) as [key, value]}
          <p><span>{key}</span> {String(value)}</p>
        {:else}
          <p class="muted">No delta metrics returned.</p>
        {/each}
      </div>
    </section>

    <section class="panel">
      <h2>Related artifacts</h2>
      <p>Validation: {formatList(proposal.validation_report_ids)}</p>
      <p>Calibration: {formatList(proposal.calibration_audit_ids)}</p>
      <p>Drift: {formatList(proposal.drift_report_ids)}</p>
      <p>Review: {formatList(proposal.model_review_report_ids)}</p>
      <p>Comparisons: {formatList(proposal.comparison_ids)}</p>
      {#if proposal.research_cycle_id}
        <p>
          Cycle:
          <a class="link mono" href={`/research/cycles/${proposal.research_cycle_id}`}>
            {proposal.research_cycle_id}
          </a>
        </p>
      {/if}
    </section>

    <section class="panel">
      <h2>Approval history and decision ledger</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Decision</th>
              <th>Status</th>
              <th>Actor</th>
              <th>Reasons</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {#each decisions as decision}
              <tr>
                <td>{decision.decision_type}</td>
                <td><StatusBadge value={decision.decision_status ?? 'recorded'} /></td>
                <td>{decision.actor ?? '-'}</td>
                <td>{formatList(decision.reason_codes)}</td>
                <td>{formatDateTime(decision.created_at)}</td>
              </tr>
            {:else}
              <tr>
                <td colspan="5" class="muted">No ledger decisions returned for this proposal.</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <JsonPanel title="Proposal payload" value={proposal} />
      <JsonPanel title="Decision ledger payload" value={decisions} />
    </section>
  {:else}
    <section class="panel">
      <p>{message}</p>
    </section>
  {/if}

  {#if lastResult}
    <section class="panel">
      <p class="muted">{message}</p>
      <JsonPanel title="Latest action response" value={lastResult} />
    </section>
  {/if}
</div>

<style>
  header,
  .activation-head {
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

  .reject-field {
    min-width: min(360px, 100%);
  }

  .danger-panel {
    display: grid;
    gap: 14px;
    border-color: rgba(255, 94, 103, 0.45);
    background: rgba(64, 24, 28, 0.45);
  }

  .activation-grid,
  .detail-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 14px;
  }

  .check-row {
    display: flex;
    min-height: 38px;
    gap: 8px;
    align-items: center;
    color: var(--text);
  }

  .panel p + p {
    margin-top: 8px;
  }
</style>
