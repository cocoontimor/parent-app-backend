<script>
  import { useForm, router } from '@inertiajs/svelte'
  import Layout from '../../lib/Layout.svelte'
  import Modal from '../../lib/Modal.svelte'

  export let course
  export let cohorts = []

  let moduleOpen = false
  let lessonOpen = false
  let lessonModuleId = ''

  const moduleForm = useForm({ course: course.id, title: '', order: 0 })
  const lessonForm = useForm({
    module: '',
    title: '',
    description: '',
    youtube_url: '',
    order: 0,
    release_offset_days: 0,
  })

  function submitModule() {
    $moduleForm.post('/elearning/modules/create/', {
      onSuccess: () => {
        moduleOpen = false
        $moduleForm.reset()
        $moduleForm.course = course.id
      },
    })
  }

  function openLesson(moduleId) {
    $lessonForm.reset()
    $lessonForm.module = moduleId
    lessonModuleId = moduleId
    lessonOpen = true
  }

  function submitLesson() {
    $lessonForm.post('/elearning/lessons/create/', {
      onSuccess: () => {
        lessonOpen = false
        $lessonForm.reset()
      },
    })
  }

  const fmtDate = (v) => (v ? new Date(v).toLocaleDateString() : '—')
</script>

<Layout>
  <div class="page-head">
    <h1>{course.title}</h1>
    <div style="display: flex; gap: 0.5rem;">
      <button class="ghost" on:click={() => router.visit('/elearning/')}>Back</button>
      <button on:click={() => (moduleOpen = true)}>Add Module</button>
    </div>
  </div>

  {#if course.description}
    <p class="hint">{course.description}</p>
  {/if}

  {#each course.modules as m}
    <div style="margin-top: 1.5rem;">
      <div class="page-head" style="margin-bottom: 0.5rem;">
        <h2>{m.title}</h2>
        <button class="ghost" on:click={() => openLesson(m.id)}>Add Lesson</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>#</th><th>Lesson</th><th>YouTube</th><th>Releases (day)</th></tr>
          </thead>
          <tbody>
            {#each m.lessons as l}
              <tr>
                <td>{l.order}</td>
                <td>{l.title}</td>
                <td><a href={l.youtube_url} target="_blank" rel="noreferrer">Link</a></td>
                <td>+{l.release_offset_days}d</td>
              </tr>
            {:else}
              <tr><td colspan="4" class="empty">No lessons yet.</td></tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {:else}
    <p class="empty" style="margin-top: 1.5rem;">No modules yet. Add one to start building the course.</p>
  {/each}

  <h2 style="margin-top: 2rem;">Cohorts on this course</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Name</th><th>Circle</th><th>Members</th><th>Released</th><th>Starts</th><th>Status</th></tr>
      </thead>
      <tbody>
        {#each cohorts as c}
          <tr>
            <td>{c.name}</td>
            <td>{c.circle_name}</td>
            <td>{c.recipient_count}</td>
            <td>{c.released_count} / {c.total_lessons}</td>
            <td>{fmtDate(c.start_date)}</td>
            <td>{c.active ? 'Active' : 'Paused'}</td>
          </tr>
          {#if c.releases && c.releases.length}
            <tr>
              <td colspan="6" style="padding: 0;">
                <table style="margin: 0;">
                  <tbody>
                    {#each c.releases as r}
                      <tr>
                        <td style="padding-left: 2rem;">↳ {r.lesson_title}</td>
                        <td colspan="4" class="hint">released {fmtDate(r.released_at)}</td>
                        <td>watched {r.completion_count}/{c.recipient_count}</td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </td>
            </tr>
          {/if}
        {:else}
          <tr><td colspan="6" class="empty">No cohorts running this course.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>

  <Modal title="Add Module" open={moduleOpen} onClose={() => (moduleOpen = false)}>
    <form on:submit|preventDefault={submitModule}>
      <label for="module-title">Title</label>
      <input id="module-title" bind:value={$moduleForm.title} required />

      <label for="module-order">Order</label>
      <input id="module-order" type="number" min="0" bind:value={$moduleForm.order} />

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (moduleOpen = false)}>Cancel</button>
        <button type="submit" disabled={$moduleForm.processing}>Create</button>
      </div>
    </form>
  </Modal>

  <Modal title="Add Lesson" open={lessonOpen} onClose={() => (lessonOpen = false)}>
    <form on:submit|preventDefault={submitLesson}>
      <label for="lesson-title">Title</label>
      <input id="lesson-title" bind:value={$lessonForm.title} required />

      <label for="lesson-url">YouTube URL</label>
      <input id="lesson-url" type="url" bind:value={$lessonForm.youtube_url} required />

      <label for="lesson-desc">Description</label>
      <textarea id="lesson-desc" rows="3" bind:value={$lessonForm.description}></textarea>

      <label for="lesson-order">Order</label>
      <input id="lesson-order" type="number" min="0" bind:value={$lessonForm.order} />

      <label for="lesson-offset">Release offset (days from cohort start)</label>
      <input id="lesson-offset" type="number" min="0" bind:value={$lessonForm.release_offset_days} />
      <p class="hint">0 = released on the cohort's start date; 7 = one week after, etc.</p>

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (lessonOpen = false)}>Cancel</button>
        <button type="submit" disabled={$lessonForm.processing}>Create</button>
      </div>
    </form>
  </Modal>
</Layout>
