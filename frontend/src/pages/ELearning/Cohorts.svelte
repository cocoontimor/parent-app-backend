<script>
  import { useForm, router } from '@inertiajs/svelte'
  import Layout from '../../lib/Layout.svelte'
  import Modal from '../../lib/Modal.svelte'
  import MultiSelect from '../../lib/MultiSelect.svelte'

  export let cohorts = []
  export let trainees = []

  let cohortOpen = false

  const cohortForm = useForm({ name: '', members: [] })

  $: traineeOptions = trainees.map((t) => ({ value: t.id, label: t.display_name || t.username }))

  function submitCohort() {
    $cohortForm.post('/elearning/cohorts/create/', {
      onSuccess: () => {
        cohortOpen = false
        $cohortForm.reset()
      },
    })
  }

  const fmtDate = (v) => (v ? new Date(v).toLocaleDateString() : '—')
</script>

<Layout>
  <div class="page-head">
    <h1>Cohorts</h1>
    <button on:click={() => (cohortOpen = true)}><i class="lni lni-plus"></i>New Cohort</button>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Name</th><th>Trainees</th><th>Course</th><th>Progress</th><th>Starts</th><th>Status</th></tr>
      </thead>
      <tbody>
        {#each cohorts as c}
          <tr class="clickable" on:click={() => router.visit(`/elearning/cohorts/${c.id}/`)}>
            <td>{c.name}</td>
            <td>{c.member_count}</td>
            <td>{c.active_run ? c.active_run.course_title : '—'}</td>
            <td>{c.active_run ? `${c.active_run.released_count} / ${c.active_run.total_lessons}` : '—'}</td>
            <td>{c.active_run ? fmtDate(c.active_run.start_date) : '—'}</td>
            <td>{c.active_run ? 'Running' : 'No course'}</td>
          </tr>
        {:else}
          <tr><td colspan="6" class="empty">No cohorts yet.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>

  <Modal title="New Cohort" open={cohortOpen} onClose={() => (cohortOpen = false)}>
    <form on:submit|preventDefault={submitCohort}>
      <label for="cohort-name">Name</label>
      <input id="cohort-name" bind:value={$cohortForm.name} required />

      <label>Trainees</label>
      <MultiSelect options={traineeOptions} bind:selected={$cohortForm.members} placeholder="Search trainees…" />
      <p class="hint">Pick the trainees for this cohort. Add a course and start it from the cohort's page.</p>

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (cohortOpen = false)}><i class="lni lni-xmark"></i>Cancel</button>
        <button type="submit" disabled={$cohortForm.processing}><i class="lni lni-check"></i>Create</button>
      </div>
    </form>
  </Modal>
</Layout>
