<script lang="ts">
  import ChartLineUpIcon from 'phosphor-svelte/lib/ChartLineUpIcon';

  let {
    title,
    value,
    detail = '',
    tone = 'neutral',
  }: {
    title: string;
    value: string;
    detail?: string;
    tone?: 'neutral' | 'green' | 'red' | 'amber';
  } = $props();
</script>

<section class={`metric ${tone}`}>
  <div>
    <span>{title}</span>
    <strong>{value}</strong>
    {#if detail}
      <small>{detail}</small>
    {/if}
  </div>
  <ChartLineUpIcon size={22} weight="duotone" />
</section>

<style>
  .metric {
    min-height: 112px;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--panel);
    padding: 16px;
    display: flex;
    justify-content: space-between;
    gap: 12px;
  }

  span,
  small {
    color: var(--muted);
    font-size: 13px;
  }

  strong {
    display: block;
    margin-top: 8px;
    font-size: 24px;
    line-height: 1.15;
    letter-spacing: 0;
  }

  small {
    display: block;
    margin-top: 8px;
  }

  .green strong {
    color: var(--green);
  }

  .red strong {
    color: var(--red);
  }

  .amber strong {
    color: var(--amber);
  }
</style>
