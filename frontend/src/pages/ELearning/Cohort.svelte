<script>
  import { useForm, router } from '@inertiajs/svelte'
  import Layout from '../../lib/Layout.svelte'
  import Modal from '../../lib/Modal.svelte'

  export let cohort
  export let runs = []
  export let current_run_id = null
  export let courses = []
  export let watched_by_course = []

  let runOpen = false

  const runForm = useForm({ course: '', start_date: '', send_hour: 14 })

  function submitRun() {
    $runForm.post(`/elearning/cohorts/${cohort.id}/runs/create/`, {
      onSuccess: () => {
        runOpen = false
        $runForm.reset()
      },
    })
  }

  const fmtDate = (v) => (v ? new Date(v).toLocaleDateString() : '—')

  // Click a course row to expand its watched grid inline.
  // Watched grid per run, keyed by run id (runs without releases have none).
  $: watchedByRun = Object.fromEntries(watched_by_course.map((c) => [c.run_id, c]))
  // Tabbed view: one tab per course, defaulting to the current run. Each tab
  // carries the run's meta (dates, progress, status) plus its watched grid.
  let activeTab = current_run_id
  $: if (activeTab == null && runs.length) activeTab = current_run_id ?? runs[0].id
  $: activeRun = runs.find((r) => r.id === activeTab)
  $: activeCourse = watchedByRun[activeTab]
</script>

<Layout>
  <div class="page-head">
    <h1>{cohort.name}</h1>
    <button class="ghost" on:click={() => router.visit('/elearning/cohorts/')}><i class="lni lni-arrow-left"></i>Back</button>
  </div>
  <p class="hint">{cohort.member_count} trainee{cohort.member_count === 1 ? '' : 's'}</p>

  <div class="page-head" style="margin-top: 1.5rem;">
    <h2>Courses</h2>
    <button on:click={() => (runOpen = true)}><i class="lni lni-plus"></i>Add course &amp; run</button>
  </div>

  {#if !runs.length}
    <p class="empty">No course running yet. Add one to start the drip.</p>
  {:else}
    <div class="seg tabs">
      {#each runs as r}
        <button class:active={activeTab === r.id} on:click={() => (activeTab = r.id)}>{r.course_title}</button>
      {/each}
    </div>

    {#if activeRun}
      <div class="run-meta">
        <span><span class="k">Started</span> {fmtDate(activeRun.start_date)}</span>
        <span><span class="k">Send hour</span> {activeRun.send_hour}:00</span>
        <span><span class="k">Progress</span> {activeRun.released_count} / {activeRun.total_lessons}</span>
        <span class="pill" class:muted={!activeRun.active}>{activeRun.active ? 'Running' : 'Ended'}</span>
      </div>
    {/if}

    {#if !activeCourse}
      <p class="empty" style="margin-top: 0.5rem;">No lessons released yet for this course.</p>
    {:else}
      <div class="table-wrap watched-wrap">
        <table>
          <thead>
            <tr>
              <th class="col-trainee">Trainee</th>
              <th class="col-watched">Watched</th>
              {#each activeCourse.lessons as l}
                <th class="col-lesson" title={`released ${fmtDate(l.released_at)}`}>{l.title}</th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#each activeCourse.rows as row}
              <tr>
                <td class="col-trainee">{row.name}</td>
                <td class="col-watched">{row.watched_count} / {activeCourse.lessons.length}</td>
                {#each row.cells as watched}
                  <td class="col-lesson" style="text-align: center; color: {watched ? '#16a34a' : '#cbd5e1'};">
                    {watched ? '✓' : '·'}
                  </td>
                {/each}
              </tr>
            {:else}
              <tr><td colspan={activeCourse.lessons.length + 2} class="empty">No trainees in this cohort.</td></tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  {/if}

  <Modal title="Add course & run" open={runOpen} onClose={() => (runOpen = false)}>
    <form on:submit|preventDefault={submitRun}>
      <label for="run-course">Course</label>
      <select id="run-course" bind:value={$runForm.course} required>
        <option value="" disabled>Select a course</option>
        {#each courses as c}
          <option value={c.id}>{c.title}</option>
        {/each}
      </select>

      <label for="run-start">Start date</label>
      <input id="run-start" type="date" bind:value={$runForm.start_date} required />

      <label for="run-send-hour">Send hour (0-23, Dili time)</label>
      <input id="run-send-hour" type="number" min="0" max="23" bind:value={$runForm.send_hour} required />
      <p class="hint">Lessons drip out from this date using each lesson's release offset.</p>

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (runOpen = false)}><i class="lni lni-xmark"></i>Cancel</button>
        <button type="submit" disabled={$runForm.processing}><i class="lni lni-check"></i>Run</button>
      </div>
    </form>
  </Modal>
</Layout>

<style>
  .tabs { flex-wrap: wrap; }

  .run-meta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 1.25rem;
    margin: 0.85rem 0;
    font-size: 0.9rem;
  }
  .run-meta .k { color: var(--muted); margin-right: 0.35rem; }
  .pill {
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    background: #dcfce7;
    color: #16a34a;
  }
  .pill.muted { background: #f1f5f9; color: var(--muted); }

  /* Freeze the Trainee + Watched columns; lesson columns scroll horizontally.
     Widths are fixed so the Watched column's sticky offset is known. */
  .watched-wrap .col-trainee {
    position: sticky;
    left: 0;
    z-index: 1;
    width: 12rem;
    min-width: 12rem;
  }
  .watched-wrap .col-watched {
    position: sticky;
    left: 12rem;
    z-index: 1;
    width: 6rem;
    min-width: 6rem;
    border-right: 1px solid var(--border);
  }
  .watched-wrap .col-lesson { min-width: 6rem; }
  /* Sticky cells need an opaque background so scrolled lessons don't bleed
     through. Header cells keep the header tint; body cells the panel colour. */
  .watched-wrap tbody td.col-trainee,
  .watched-wrap tbody td.col-watched { background: var(--panel); }
  .watched-wrap thead th.col-trainee,
  .watched-wrap thead th.col-watched { z-index: 2; }
</style>
