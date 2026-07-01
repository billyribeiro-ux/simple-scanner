<script lang="ts">
  import TrendUpIcon from 'phosphor-svelte/lib/TrendUpIcon';

  let modelVersion = $state('active');
  let start = $state('2026-05-01');
  let end = $state('2026-06-30');
  let symbols = $state('AMZN,AAPL,TSLA,SPY,QQQ');
  let ran = $state(false);
</script>

<svelte:head>
  <title>Backtest | Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <TrendUpIcon size={28} weight="duotone" />
    <h1>Backtest lab</h1>
  </header>

  <section class="panel form-grid">
    <label class="field">Model <input bind:value={modelVersion} /></label>
    <label class="field">Start <input type="date" bind:value={start} /></label>
    <label class="field">End <input type="date" bind:value={end} /></label>
    <label class="field">Symbols <input bind:value={symbols} /></label>
  </section>

  <button class="btn primary" onclick={() => (ran = true)}>Run Backtest</button>

  <section class="grid">
    <div class="panel"><span>Trades</span><strong>{ran ? '0' : '-'}</strong></div>
    <div class="panel"><span>Expectancy</span><strong>{ran ? 'Pending data' : '-'}</strong></div>
    <div class="panel"><span>Drawdown</span><strong>{ran ? 'Pending data' : '-'}</strong></div>
  </section>

  <section class="panel curve">
    <span>R Curve</span>
    <div></div>
  </section>
</div>

<style>
  header {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  h1 {
    margin: 0;
  }

  .form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 14px;
  }

  .panel span {
    color: var(--muted);
  }

  .panel strong {
    display: block;
    margin-top: 8px;
  }

  .curve div {
    margin-top: 14px;
    height: 180px;
    border: 1px solid var(--line);
    border-radius: 6px;
    background:
      linear-gradient(180deg, transparent 49%, #244050 50%, transparent 51%),
      linear-gradient(90deg, rgba(43, 213, 118, 0.1), rgba(255, 94, 103, 0.1));
  }
</style>
