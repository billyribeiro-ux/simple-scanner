<script lang="ts">
  import BrainIcon from 'phosphor-svelte/lib/BrainIcon';
  import ShieldCheckIcon from 'phosphor-svelte/lib/ShieldCheckIcon';
</script>

<svelte:head>
  <title>Research Governance | Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <BrainIcon size={28} weight="duotone" />
    <div>
      <h1>Research governance</h1>
      <p>Controlled cycles, model proposals, and explicit scanner model activation review.</p>
    </div>
  </header>

  <section class="panel notice">
    <ShieldCheckIcon size={22} weight="duotone" />
    <div>
      <strong>No broker execution</strong>
      <span
        >Approval and activation are separate steps. Activation updates the scanner model only.</span
      >
    </div>
  </section>

  <section class="grid">
    <a class="panel link-card" href="/research/cycles">
      <strong>Research cycles</strong>
      <span>Create, dry-run, run, inspect, and export controlled research cycles.</span>
    </a>
    <a class="panel link-card" href="/research/proposals">
      <strong>Model proposals</strong>
      <span>Review champion/challenger evidence and gate results before any approval.</span>
    </a>
    <a class="panel link-card" href="/research/decision-ledger">
      <strong>Decision ledger</strong>
      <span>Inspect the append-only record of cycle, proposal, and activation decisions.</span>
    </a>
    <a class="panel link-card" href="/operations">
      <strong>Operations status</strong>
      <span>Read backend persistence, active model, stale window, and data quality status.</span>
    </a>
  </section>
</div>

<style>
  header,
  .notice {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  h1,
  p {
    margin: 0;
  }

  p,
  span {
    color: var(--muted);
  }

  .notice strong,
  .notice span,
  .link-card strong,
  .link-card span {
    display: block;
  }

  .link-card {
    min-height: 116px;
  }

  .link-card strong {
    color: var(--text);
    margin-bottom: 8px;
  }
</style>
