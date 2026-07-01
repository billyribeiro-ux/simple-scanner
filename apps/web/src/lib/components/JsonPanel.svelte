<script lang="ts">
  import { prettyJson } from '$lib/governance';

  let { title = 'Details', value }: { title?: string; value: unknown } = $props();
</script>

<details class="json-panel">
  <summary>{title}</summary>
  <pre>{prettyJson(value)}</pre>
</details>

<style>
  .json-panel {
    border-top: 1px solid var(--line);
    padding-top: 10px;
  }

  summary {
    color: var(--text);
    cursor: pointer;
  }

  pre {
    max-height: 320px;
    overflow: auto;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: #0c131a;
    color: #cfe3f3;
    padding: 12px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
</style>
