<script>
  import { router } from '@inertiajs/svelte'
  import Layout from '../../lib/Layout.svelte'

  export let cohort
  export let lessons = []
  export let rows = []

  const fmtDate = (v) => (v ? new Date(v).toLocaleDateString() : '—')
</script>

<Layout>
  <div class="page-head">
    <h1>{cohort.name}</h1>
    <button class="ghost" on:click={() => router.visit('/elearning/')}>Back</button>
  </div>
  <p class="hint">
    {cohort.course_title} · {cohort.circle_name} · starts {fmtDate(cohort.start_date)}
    · {cohort.released_count}/{cohort.total_lessons} lessons released
  </p>

  {#if !lessons.length}
    <p class="empty" style="margin-top: 1.5rem;">No lessons released yet.</p>
  {:else}
    <div class="table-wrap" style="margin-top: 1rem;">
      <table>
        <thead>
          <tr>
            <th>Parent</th>
            {#each lessons as l}
              <th title={`released ${fmtDate(l.released_at)}`}>{l.title}</th>
            {/each}
            <th>Watched</th>
          </tr>
        </thead>
        <tbody>
          {#each rows as r}
            <tr>
              <td>{r.name}</td>
              {#each r.cells as watched}
                <td style="text-align: center; color: {watched ? '#16a34a' : '#cbd5e1'};">
                  {watched ? '✓' : '·'}
                </td>
              {/each}
              <td>{r.watched_count} / {lessons.length}</td>
            </tr>
          {:else}
            <tr><td colspan={lessons.length + 2} class="empty">No parents in this cohort's circle.</td></tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</Layout>
