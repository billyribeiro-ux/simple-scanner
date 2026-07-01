<script lang="ts">
  import GearSixIcon from 'phosphor-svelte/lib/GearSixIcon';
  import { fetchConfig, fetchProviderHealth } from '$lib/api';
  import type { AppConfig, ProviderHealth } from '$lib/types';

  let config = $state<AppConfig | null>({
    app_name: 'Adaptive Market Decoder',
    default_symbols: ['AMZN', 'AAPL', 'TSLA', 'SPY', 'QQQ', 'IWM', 'NVDA', 'GOOGL', 'BABA', 'SHOP'],
    timezone: 'America/New_York',
    min_confidence: 0.7,
    fmp_api_key_configured: false,
  });
  let provider = $state<ProviderHealth>({ status: 'not checked' });
  let symbols = $state('AMZN,AAPL,TSLA,SPY,QQQ,IWM,NVDA,GOOGL,BABA,SHOP');
  let session = $state('RTH');
  let rateLimit = $state(15);

  async function refresh() {
    config = await fetchConfig();
    provider = await fetchProviderHealth();
    symbols = config.default_symbols.join(',');
  }
</script>

<svelte:head>
  <title>Settings | Adaptive Market Decoder</title>
</svelte:head>

<div class="page">
  <header>
    <GearSixIcon size={28} weight="duotone" />
    <h1>Settings</h1>
    <button class="btn" onclick={refresh}>Refresh</button>
  </header>

  <section class="grid">
    <div class="panel">
      <span>API key</span><strong
        >{config?.fmp_api_key_configured ? 'Configured' : 'Missing'}</strong
      >
    </div>
    <div class="panel"><span>Provider</span><strong>{provider.status}</strong></div>
    <div class="panel">
      <span>Timezone</span><strong>{config?.timezone ?? 'America/New_York'}</strong>
    </div>
  </section>

  <section class="panel form-grid">
    <label class="field">Symbols <input bind:value={symbols} /></label>
    <label class="field"
      >Session <select bind:value={session}
        ><option>RTH</option><option>Premarket + RTH</option></select
      ></label
    >
    <label class="field"
      >REST poll seconds <input type="number" bind:value={rateLimit} min="5" max="120" /></label
    >
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

  .panel span {
    color: var(--muted);
  }

  .panel strong {
    display: block;
    margin-top: 8px;
  }

  .form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 14px;
  }
</style>
