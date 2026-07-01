<script lang="ts">
  let { value = 'unknown' }: { value?: string | null } = $props();

  function tone(status: string | null | undefined) {
    const normalized = String(status ?? '').toLowerCase();
    if (
      ['ok', 'completed', 'approved', 'approved_for_activation', 'pass', 'active', 'created'].some(
        (item) => normalized.includes(item),
      )
    ) {
      return 'good';
    }
    if (
      ['blocked', 'rejected', 'error', 'failed', 'stale'].some((item) => normalized.includes(item))
    ) {
      return 'bad';
    }
    if (
      ['review', 'pending', 'watch', 'dry_run', 'proposed'].some((item) =>
        normalized.includes(item),
      )
    ) {
      return 'warn';
    }
    return 'neutral';
  }
</script>

<span
  class="badge"
  class:good={tone(value) === 'good'}
  class:bad={tone(value) === 'bad'}
  class:warn={tone(value) === 'warn'}
>
  {value ?? 'unknown'}
</span>

<style>
  .badge {
    display: inline-flex;
    align-items: center;
    width: fit-content;
    min-height: 24px;
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 3px 9px;
    color: var(--muted);
    background: #0c131a;
    font-size: 12px;
    line-height: 1.3;
    overflow-wrap: anywhere;
  }

  .good {
    border-color: rgba(43, 213, 118, 0.45);
    color: var(--green);
    background: rgba(43, 213, 118, 0.08);
  }

  .bad {
    border-color: rgba(255, 94, 103, 0.45);
    color: var(--red);
    background: rgba(255, 94, 103, 0.08);
  }

  .warn {
    border-color: rgba(244, 187, 68, 0.45);
    color: var(--amber);
    background: rgba(244, 187, 68, 0.08);
  }
</style>
