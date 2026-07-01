<script lang="ts">
  import PlayIcon from 'phosphor-svelte/lib/PlayIcon';
  import StopIcon from 'phosphor-svelte/lib/StopIcon';
  import { fetchScannerStatus, fetchSignals, startScanner, stopScanner } from '$lib/api';
  import SignalTable from '$lib/components/SignalTable.svelte';
  import type { ScannerStatus, Signal } from '$lib/types';

  let threshold = $state(0.7);
  let status = $state<ScannerStatus>({
    running: false,
    started_at: null,
    latest_count: 0,
    last_error: null,
  });
  let signals = $state<Signal[]>([]);

  async function refresh() {
    status = await fetchScannerStatus();
    signals = await fetchSignals();
  }

  async function start() {
    status = await startScanner(threshold);
    await refresh();
  }

  async function stop() {
    status = await stopScanner();
    await refresh();
  }
</script>

<svelte:head>
  <title>Live Scanner | Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <h1>Live scanner</h1>
    <span class:online={status.running}>{status.running ? 'Running' : 'Stopped'}</span>
  </header>

  <section class="panel toolbar">
    <label class="field"
      >Confidence threshold <input
        type="number"
        step="0.01"
        min="0"
        max="1"
        bind:value={threshold}
      /></label
    >
    <button class="btn primary" onclick={start}><PlayIcon size={18} /> Start</button>
    <button class="btn danger" onclick={stop}><StopIcon size={18} /> Stop</button>
    <button class="btn" onclick={refresh}>Refresh</button>
  </section>

  <SignalTable {signals} />

  <section class="panel">
    <h2>Signal Details</h2>
    <p>{signals[0]?.reasons.join(' ') ?? 'Select a live signal after the scanner emits one.'}</p>
    {#if signals[0]?.warnings.length}
      <strong>Warnings</strong>
      <p>{signals[0].warnings.join(' ')}</p>
    {/if}
  </section>
</div>

<style>
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  h1,
  h2,
  p {
    margin: 0;
  }

  h2 {
    margin-bottom: 10px;
  }

  p {
    color: var(--muted);
  }

  header span {
    color: var(--muted);
  }

  .online {
    color: var(--green);
  }
</style>
