<script>
  import { router } from '@inertiajs/svelte'
  import Layout from '../../lib/Layout.svelte'

  export let circle
  export let date
  export let roster = []

  const STATUSES = [
    { value: 'present', label: 'Present' },
    { value: 'absent', label: 'Absent' },
  ]

  let day = date
  let rows = []
  let processing = false
  // Re-seed the editable rows whenever the server sends a new roster (i.e. on
  // date navigation), so saved statuses for that day show up.
  $: seed(roster)
  function seed(r) {
    rows = r.map((x) => ({ ...x }))
  }

  function setStatus(i, value) {
    rows[i].status = value
    rows = rows
  }

  function markAll(value) {
    rows = rows.map((r) => ({ ...r, status: value }))
  }

  function onDate() {
    router.get(`/classes/${circle.id}/attendance/`, { date: day }, { preserveScroll: true })
  }

  function save() {
    processing = true
    router.post(
      `/classes/${circle.id}/attendance/save/`,
      { date: day, roster: rows },
      { preserveScroll: true, onFinish: () => (processing = false) }
    )
  }

  $: counts = rows.reduce(
    (acc, r) => ((acc[r.status] = (acc[r.status] || 0) + 1), acc),
    {}
  )
</script>

<Layout>
  <div class="page-head">
    <h1>Attendance — {circle.name}</h1>
    <button class="ghost" on:click={() => router.visit('/classes/')}><i class="lni lni-arrow-left"></i>Back</button>
  </div>

  <div class="toolbar">
    <label class="date-field">
      <span>Date</span>
      <input type="date" bind:value={day} on:change={onDate} />
    </label>
    <div class="summary">
      <span class="pill present">{counts.present || 0} present</span>
      <span class="pill absent">{counts.absent || 0} absent</span>
    </div>
    <button class="ghost" on:click={() => markAll('present')}>Mark all present</button>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Child</th><th style="width: 1%;">Status</th></tr>
      </thead>
      <tbody>
        {#each rows as r, i}
          <tr>
            <td>{r.name}</td>
            <td>
              <div class="seg status-seg">
                {#each STATUSES as s}
                  <button
                    class:active={r.status === s.value}
                    class="s-{s.value}"
                    on:click={() => setStatus(i, s.value)}
                  >{s.label}</button>
                {/each}
              </div>
            </td>
          </tr>
        {:else}
          <tr><td colspan="2" class="empty">No children in this class.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>

  {#if rows.length}
    <div class="save-bar">
      <button disabled={processing} on:click={save}><i class="lni lni-check"></i>Save attendance</button>
    </div>
  {/if}
</Layout>

<style>
  .toolbar {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
  }
  .date-field { display: flex; align-items: center; gap: 0.5rem; }
  .date-field span { color: var(--muted); font-size: 0.9rem; }
  .date-field input { margin: 0; width: auto; }
  .summary { display: flex; gap: 0.5rem; margin-left: auto; }
  .pill {
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    background: #f1f5f9;
    color: var(--muted);
  }
  .pill.present { background: #dcfce7; color: #16a34a; }
  .pill.absent { background: #fee2e2; color: #dc2626; }

  /* Reuse the segmented-control look; colour the active choice by status. */
  .status-seg button.active.s-present { background: #16a34a; color: #fff; }
  .status-seg button.active.s-absent { background: #dc2626; color: #fff; }

  .save-bar { display: flex; justify-content: flex-end; margin-top: 1rem; }
</style>
