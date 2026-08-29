<script>
  import { useForm, router } from '@inertiajs/svelte'
  import Layout from '../../lib/Layout.svelte'
  import Modal from '../../lib/Modal.svelte'

  export let courses = []
  export let cohorts = []
  export let circles = []

  let courseOpen = false
  let cohortOpen = false

  const courseForm = useForm({ title: '', description: '' })
  const cohortForm = useForm({ name: '', course: '', circle: '', start_date: '', send_hour: 14 })

  function submitCourse() {
    $courseForm.post('/elearning/courses/create/', {
      onSuccess: () => {
        courseOpen = false
        $courseForm.reset()
      },
    })
  }

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
    <h1>E-Learning</h1>
    <div style="display: flex; gap: 0.5rem;">
      <button class="ghost" on:click={() => (courseOpen = true)}>New Course</button>
      <button on:click={() => (cohortOpen = true)}>New Cohort</button>
    </div>
  </div>

  <h2>Courses</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Title</th><th>Modules</th><th>Lessons</th></tr>
      </thead>
      <tbody>
        {#each courses as c}
          <tr class="clickable" on:click={() => router.visit(`/elearning/courses/${c.id}/`)}>
            <td>{c.title}</td>
            <td>{c.modules.length}</td>
            <td>{c.lesson_count}</td>
          </tr>
        {:else}
          <tr><td colspan="3" class="empty">No courses yet.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>

  <h2 style="margin-top: 2rem;">Cohorts</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Name</th><th>Course</th><th>Circle</th><th>Members</th><th>Progress</th><th>Starts</th><th>Status</th></tr>
      </thead>
      <tbody>
        {#each cohorts as c}
          <tr class="clickable" on:click={() => router.visit(`/elearning/cohorts/${c.id}/`)}>
            <td>{c.name}</td>
            <td>{c.course_title}</td>
            <td>{c.circle_name}</td>
            <td>{c.recipient_count}</td>
            <td>{c.released_count} / {c.total_lessons}</td>
            <td>{fmtDate(c.start_date)}</td>
            <td>{c.active ? 'Active' : 'Paused'}</td>
          </tr>
        {:else}
          <tr><td colspan="7" class="empty">No cohorts yet.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>

  <Modal title="New Course" open={courseOpen} onClose={() => (courseOpen = false)}>
    <form on:submit|preventDefault={submitCourse}>
      <label for="course-title">Title</label>
      <input id="course-title" bind:value={$courseForm.title} required />

      <label for="course-desc">Description</label>
      <textarea id="course-desc" rows="3" bind:value={$courseForm.description}></textarea>

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (courseOpen = false)}>Cancel</button>
        <button type="submit" disabled={$courseForm.processing}>Create</button>
      </div>
    </form>
  </Modal>

  <Modal title="New Cohort" open={cohortOpen} onClose={() => (cohortOpen = false)}>
    <form on:submit|preventDefault={submitCohort}>
      <label for="cohort-name">Name</label>
      <input id="cohort-name" bind:value={$cohortForm.name} required />

      <label for="cohort-course">Course</label>
      <select id="cohort-course" bind:value={$cohortForm.course} required>
        <option value="" disabled>Select a course</option>
        {#each courses as c}
          <option value={c.id}>{c.title}</option>
        {/each}
      </select>

      <label for="cohort-circle">Circle (recipients)</label>
      <select id="cohort-circle" bind:value={$cohortForm.circle} required>
        <option value="" disabled>Select a circle</option>
        {#each circles as c}
          <option value={c.id}>{c.name}</option>
        {/each}
      </select>

      <label for="cohort-start">Start date</label>
      <input id="cohort-start" type="date" bind:value={$cohortForm.start_date} required />

      <label for="cohort-send-hour">Send hour (0-23, Dili time)</label>
      <input id="cohort-send-hour" type="number" min="0" max="23" bind:value={$cohortForm.send_hour} required />
      <p class="hint">Lessons drip out from this date using each lesson's release offset.</p>

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (cohortOpen = false)}>Cancel</button>
        <button type="submit" disabled={$cohortForm.processing}>Create</button>
      </div>
    </form>
  </Modal>
</Layout>
