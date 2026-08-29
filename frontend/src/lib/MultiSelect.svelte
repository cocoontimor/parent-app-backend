<script>
  // Searchable multi-select. Type to filter; picks show as removable chips.
  // Only the first LIMIT matches render, so it stays fast on long lists.
  export let options = [] // [{ value, label }]
  export let selected = [] // [value]  (bindable)
  export let placeholder = 'Search…'

  const LIMIT = 50
  let query = ''

  $: selectedSet = new Set(selected)
  $: chips = options.filter((o) => selectedSet.has(o.value))
  $: q = query.trim().toLowerCase()
  $: matches = options.filter(
    (o) => !selectedSet.has(o.value) && o.label.toLowerCase().includes(q)
  )
  $: shown = matches.slice(0, LIMIT)

  const add = (v) => (selected = [...selected, v])
  const remove = (v) => (selected = selected.filter((x) => x !== v))
</script>

<div class="ms">
  {#if chips.length}
    <div class="ms-chips">
      {#each chips as c}
        <span class="ms-chip">
          {c.label}
          <button type="button" on:click={() => remove(c.value)}>✕</button>
        </span>
      {/each}
    </div>
  {/if}

  <input class="ms-search" type="text" bind:value={query} {placeholder} />
  <div class="ms-list">
    {#each shown as o}
      <button type="button" class="ms-option" on:click={() => add(o.value)}>{o.label}</button>
    {:else}
      <div class="ms-empty">{q ? 'No matches' : 'No options'}</div>
    {/each}
    {#if matches.length > shown.length}
      <div class="ms-more">+{matches.length - shown.length} more — keep typing to narrow</div>
    {/if}
  </div>
</div>
