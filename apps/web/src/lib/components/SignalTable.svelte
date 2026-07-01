<script lang="ts">
  import type { Signal } from '$lib/types';

  let { signals = [] }: { signals?: Signal[] } = $props();
</script>

<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>Ticker</th>
        <th>Side</th>
        <th>Grade</th>
        <th>Entry</th>
        <th>Stop</th>
        <th>T1</th>
        <th>Conf</th>
        <th>Setup</th>
        <th>Regime</th>
      </tr>
    </thead>
    <tbody>
      {#if signals.length === 0}
        <tr>
          <td colspan="9" class="empty">No live signals yet.</td>
        </tr>
      {:else}
        {#each signals as signal}
          <tr>
            <td>{signal.ticker}</td>
            <td class:long={signal.side === 'LONG'} class:short={signal.side === 'SHORT'}
              >{signal.side}</td
            >
            <td>{signal.signal_grade}</td>
            <td>{signal.entry_price?.toFixed(2) ?? '-'}</td>
            <td>{signal.stop_price?.toFixed(2) ?? '-'}</td>
            <td>{signal.target_1?.toFixed(2) ?? '-'}</td>
            <td>{Math.round(signal.confidence_score * 100)}%</td>
            <td>{signal.setup_type}</td>
            <td>{signal.market_regime}</td>
          </tr>
        {/each}
      {/if}
    </tbody>
  </table>
</div>

<style>
  .table-wrap {
    overflow-x: auto;
    border: 1px solid var(--line);
    border-radius: 8px;
  }

  table {
    width: 100%;
    min-width: 860px;
    border-collapse: collapse;
    background: var(--panel);
  }

  th,
  td {
    padding: 11px 12px;
    text-align: left;
    border-bottom: 1px solid var(--line);
    font-size: 13px;
    white-space: nowrap;
  }

  th {
    color: var(--muted);
    background: var(--panel-2);
    font-weight: 600;
  }

  .long {
    color: var(--green);
  }

  .short {
    color: var(--red);
  }

  .empty {
    color: var(--muted);
    text-align: center;
  }
</style>
