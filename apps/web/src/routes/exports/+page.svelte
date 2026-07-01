<script lang="ts">
  import DownloadSimpleIcon from 'phosphor-svelte/lib/DownloadSimpleIcon';
  import { exportSignalsCsv, exportSignalsXlsx } from '$lib/api';

  let message = $state('No export requested yet.');

  async function csv() {
    const result = await exportSignalsCsv();
    message = `${result.status}: ${result.path}`;
  }

  async function xlsx() {
    const result = await exportSignalsXlsx();
    message = `${result.status}: ${result.path}`;
  }
</script>

<svelte:head>
  <title>Exports | Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <DownloadSimpleIcon size={28} weight="duotone" />
    <h1>Exports</h1>
  </header>

  <section class="grid">
    <button class="panel export" onclick={csv}>Export Signals CSV</button>
    <button class="panel export" onclick={xlsx}>Export Signals XLSX</button>
    <button class="panel export" onclick={xlsx}>Export Backtest XLSX</button>
    <button class="panel export" onclick={xlsx}>Export Daily Review XLSX</button>
  </section>

  <section class="panel">
    <h2>Export History</h2>
    <p>{message}</p>
  </section>
</div>

<style>
  header {
    display: flex;
    gap: 12px;
    align-items: center;
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

  .export {
    color: var(--text);
    text-align: left;
    min-height: 88px;
  }
</style>
