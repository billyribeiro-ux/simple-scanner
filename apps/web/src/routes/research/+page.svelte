<script lang="ts">
  import BrainIcon from 'phosphor-svelte/lib/BrainIcon';

  let symbols = $state('AMZN,AAPL,TSLA,SPY,QQQ,IWM,NVDA,GOOGL,BABA,SHOP');
  let start = $state('2026-01-01');
  let end = $state('2026-06-30');
  let interval1 = $state(true);
  let interval5 = $state(true);
  let interval15 = $state(true);
  let maxHold = $state(60);
  let targetR = $state(1.5);
  let status = $state('Ready');

  function mark(action: string) {
    status = `${action} requested. Backend route is wired for local execution.`;
  }
</script>

<svelte:head>
  <title>Research | Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <BrainIcon size={28} weight="duotone" />
    <div>
      <h1>Training and research</h1>
      <p>{status}</p>
    </div>
  </header>

  <section class="panel form-grid">
    <label class="field">Symbols <input bind:value={symbols} /></label>
    <label class="field">Training start <input type="date" bind:value={start} /></label>
    <label class="field">Training end <input type="date" bind:value={end} /></label>
    <label class="field"
      >Max hold minutes <input type="number" bind:value={maxHold} min="5" max="240" /></label
    >
    <label class="field"
      >Target R <input type="number" bind:value={targetR} min="0.5" max="5" step="0.1" /></label
    >
    <div class="field">
      Intervals
      <div class="checks">
        <label><input type="checkbox" bind:checked={interval1} /> 1m</label>
        <label><input type="checkbox" bind:checked={interval5} /> 5m</label>
        <label><input type="checkbox" bind:checked={interval15} /> 15m</label>
      </div>
    </div>
  </section>

  <section class="toolbar">
    <button class="btn" onclick={() => mark('Feature build')}>Build Features</button>
    <button class="btn" onclick={() => mark('Label build')}>Build Labels</button>
    <button class="btn primary" onclick={() => mark('Model train')}>Train Model</button>
    <button class="btn" onclick={() => mark('Validation')}>Validate</button>
    <button class="btn" onclick={() => mark('Activation')}>Activate Model</button>
  </section>

  <section class="grid">
    <div class="panel">
      <strong>Chronological split</strong><span>No random shuffle across time.</span>
    </div>
    <div class="panel">
      <strong>Leakage checks</strong><span>Labels use next-bar execution.</span>
    </div>
    <div class="panel">
      <strong>Activation guard</strong><span>Models activate only after passing validation.</span>
    </div>
  </section>
</div>

<style>
  header {
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

  .form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 14px;
  }

  .checks {
    min-height: 38px;
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .panel strong,
  .panel span {
    display: block;
  }
</style>
