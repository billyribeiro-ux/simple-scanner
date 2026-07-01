<script lang="ts">
  import '../app.css';
  import ChartLineUpIcon from 'phosphor-svelte/lib/ChartLineUpIcon';

  const links = [
    ['/', 'Dashboard'],
    ['/research', 'Research'],
    ['/backtest', 'Backtest'],
    ['/scanner', 'Scanner'],
    ['/exports', 'Exports'],
    ['/settings', 'Settings'],
  ] as const;
</script>

<div class="shell">
  <aside>
    <div class="brand">
      <ChartLineUpIcon size={28} weight="duotone" />
      <div>
        <strong>Adaptive Market Decoder</strong>
        <span>Signal research terminal</span>
      </div>
    </div>
    <nav>
      {#each links as [href, label]}
        <a {href}>{label}</a>
      {/each}
    </nav>
  </aside>
  <main>
    <slot />
  </main>
</div>

<style>
  .shell {
    min-height: 100vh;
    display: grid;
    grid-template-columns: 248px minmax(0, 1fr);
  }

  aside {
    border-right: 1px solid var(--line);
    background: #081018;
    padding: 18px;
  }

  main {
    padding: 22px;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 22px;
  }

  .brand strong,
  .brand span {
    display: block;
  }

  .brand span {
    color: var(--muted);
    font-size: 12px;
    margin-top: 3px;
  }

  nav {
    display: grid;
    gap: 6px;
  }

  nav a {
    min-height: 38px;
    display: flex;
    align-items: center;
    border-radius: 6px;
    padding: 8px 10px;
    color: var(--muted);
  }

  nav a:hover {
    color: var(--text);
    background: var(--panel);
  }

  @media (max-width: 760px) {
    .shell {
      grid-template-columns: 1fr;
    }

    aside {
      border-right: 0;
      border-bottom: 1px solid var(--line);
    }

    nav {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }
</style>
