<script>
  import { useForm, router } from '@inertiajs/svelte'
  import Layout from '../../lib/Layout.svelte'
  import Modal from '../../lib/Modal.svelte'
  import ConfirmModal from '../../lib/ConfirmModal.svelte'

  export let course

  let view = 'modules' // 'modules' | 'timeline'

  // Timeline dates are relative to a start date. A course runs for many cohorts
  // with different starts, so we anchor to a picked date (defaulting to today)
  // and show each release point's actual calendar date.
  const _t = new Date()
  let anchorDate = `${_t.getFullYear()}-${String(_t.getMonth() + 1).padStart(2, '0')}-${String(_t.getDate()).padStart(2, '0')}`
  const releaseDate = (day) => {
    const d = new Date(`${anchorDate}T00:00:00`)
    d.setDate(d.getDate() + day)
    return d
  }
  const fmtShort = (d) => d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })

  // Flatten every lesson in delivery order (module order, then lesson order),
  // accumulating each lesson's release_offset_days into a cumulative release
  // day — the offset is the gap after the previous lesson.
  $: allLessons = (() => {
    let day = 0
    const out = []
    for (const m of course.modules) {
      for (const l of m.lessons) {
        day += l.release_offset_days
        out.push({ ...l, module: m.title, releaseDay: day })
      }
    }
    return out
  })()
  // Group by cumulative release day so lessons that unlock together stack.
  $: timeline = Object.values(
    allLessons.reduce((acc, l) => {
      const day = l.releaseDay
      ;(acc[day] ??= { day, lessons: [] }).lessons.push(l)
      return acc
    }, {})
  ).sort((a, b) => a.day - b.day)
  // Running total of lessons released up to and including each point.
  $: cumulative = timeline.reduce((run, pt) => {
    run.push((run.length ? run[run.length - 1] : 0) + pt.lessons.length)
    return run
  }, [])

  let courseOpen = false
  let moduleOpen = false
  let moduleEditOpen = false
  let lessonOpen = false
  let lessonEditOpen = false

  const courseForm = useForm({ title: course.title, description: course.description || '' })
  const moduleForm = useForm({ course: course.id, title: '' })
  const moduleEditForm = useForm({ id: '', title: '' })
  const lessonForm = useForm({ module: '', title: '', description: '', youtube_url: '', release_offset_days: 0 })
  const lessonEditForm = useForm({ id: '', title: '', description: '', youtube_url: '', release_offset_days: 0 })

  function submitCourse() {
    $courseForm.post(`/elearning/courses/${course.id}/edit/`, {
      onSuccess: () => (courseOpen = false),
    })
  }

  function submitModule() {
    $moduleForm.post('/elearning/modules/create/', {
      onSuccess: () => {
        moduleOpen = false
        $moduleForm.reset()
        $moduleForm.course = course.id
      },
    })
  }

  function openEditModule(m) {
    $moduleEditForm.id = m.id
    $moduleEditForm.title = m.title
    moduleEditOpen = true
  }

  function submitModuleEdit() {
    $moduleEditForm.post(`/elearning/modules/${$moduleEditForm.id}/edit/`, {
      onSuccess: () => (moduleEditOpen = false),
    })
  }

  function openLesson(moduleId) {
    $lessonForm.reset()
    $lessonForm.module = moduleId
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

  function openEditLesson(l) {
    $lessonEditForm.id = l.id
    $lessonEditForm.title = l.title
    $lessonEditForm.description = l.description || ''
    $lessonEditForm.youtube_url = l.youtube_url
    $lessonEditForm.release_offset_days = l.release_offset_days
    lessonEditOpen = true
  }

  function submitLessonEdit() {
    $lessonEditForm.post(`/elearning/lessons/${$lessonEditForm.id}/edit/`, {
      onSuccess: () => (lessonEditOpen = false),
    })
  }

  const reorder = (kind, id, direction) =>
    router.post(`/elearning/${kind}/${id}/reorder/`, { direction }, { preserveScroll: true })

  // { kind: 'modules' | 'lessons', id, label, name } pending soft-delete.
  let confirmTarget = null
  const askDelete = (kind, id, label, name) => (confirmTarget = { kind, id, label, name })

  function doDelete() {
    const { kind, id } = confirmTarget
    router.post(`/elearning/${kind}/${id}/delete/`, {}, { preserveScroll: true })
    confirmTarget = null
  }
</script>

<Layout>
  <div class="page-head">
    <div class="title-line">
      <h1>{course.title}</h1>
      <button class="icon-btn" title="Edit course" aria-label="Edit course" on:click={() => (courseOpen = true)}><i class="lni lni-pencil-1"></i></button>
    </div>
    <div style="display: flex; gap: 0.5rem;">
      <button class="ghost" on:click={() => router.visit('/elearning/courses/')}><i class="lni lni-arrow-left"></i>Back</button>
      <button on:click={() => (moduleOpen = true)}><i class="lni lni-plus"></i>Add Module</button>
    </div>
  </div>

  {#if course.description}
    <p class="hint" style="margin: 0 0 0.5rem;">{course.description}</p>
  {/if}

  <div class="seg" style="margin: 0.75rem 0 0.25rem;">
    <button class:active={view === 'modules'} on:click={() => (view = 'modules')}><i class="lni lni-layers-1"></i>Modules</button>
    <button class:active={view === 'timeline'} on:click={() => (view = 'timeline')}><i class="lni lni-calendar-days"></i>Timeline</button>
  </div>

  {#if view === 'timeline'}
    {#if timeline.length}
      <div class="tl-anchor">
        <label for="tl-start">Starts</label>
        <input id="tl-start" type="date" bind:value={anchorDate} />
        <span class="hint">Dates are relative to this start; pick a cohort's start date to preview its schedule.</span>
      </div>
      <div class="timeline">
        {#each timeline as pt, i}
          <div class="tl-point">
            <div class="tl-axis"><span class="tl-dot"></span></div>
            <div class="tl-day">
              {fmtShort(releaseDate(pt.day))}
              <span class="tl-offset">+{pt.day}d</span>
            </div>
            <div class="tl-card">
              <div class="tl-head">
                <span class="tl-count">{pt.lessons.length} lesson{pt.lessons.length === 1 ? '' : 's'}</span>
                <span class="tl-cumulative">{cumulative[i]}/{allLessons.length}</span>
              </div>
              <ul class="tl-lessons">
                {#each pt.lessons as l}
                  <li>
                    <span class="tl-title">{l.title}</span>
                    <span class="tl-module">{l.module}</span>
                  </li>
                {/each}
              </ul>
            </div>
          </div>
        {/each}
      </div>
    {:else}
      <p class="empty" style="margin-top: 1.5rem;">No lessons yet. Add lessons to see the release timeline.</p>
    {/if}
  {:else}
  {#each course.modules as m, mi}
    <div class="module-card">
      <div class="module-bar">
        <div class="module-left">
          <div class="reorder">
            <button class="icon-btn ghost" title="Move up" aria-label="Move module up" disabled={mi === 0} on:click={() => reorder('modules', m.id, 'up')}><i class="lni lni-chevron-up"></i></button>
            <button class="icon-btn ghost" title="Move down" aria-label="Move module down" disabled={mi === course.modules.length - 1} on:click={() => reorder('modules', m.id, 'down')}><i class="lni lni-chevron-down"></i></button>
          </div>
          <h2>{m.title}</h2>
        </div>
        <div class="row-actions">
          <button class="icon-btn" title="Add lesson" aria-label="Add lesson" on:click={() => openLesson(m.id)}><i class="lni lni-plus"></i></button>
          <button class="icon-btn" title="Edit module" aria-label="Edit module" on:click={() => openEditModule(m)}><i class="lni lni-pencil-1"></i></button>
          <button class="icon-btn danger" title="Delete module" aria-label="Delete module" on:click={() => askDelete('modules', m.id, 'module', m.title)}><i class="lni lni-trash-3"></i></button>
        </div>
      </div>
      <table>
        <thead>
          <tr><th style="width: 1%;">Order</th><th>Lesson</th><th>YouTube</th><th>After prev. (days)</th><th style="width: 1%;">Actions</th></tr>
        </thead>
        <tbody>
          {#each m.lessons as l, li}
            <tr>
              <td>
                <div class="reorder">
                  <button class="icon-btn ghost" title="Move up" aria-label="Move lesson up" disabled={li === 0} on:click={() => reorder('lessons', l.id, 'up')}><i class="lni lni-chevron-up"></i></button>
                  <button class="icon-btn ghost" title="Move down" aria-label="Move lesson down" disabled={li === m.lessons.length - 1} on:click={() => reorder('lessons', l.id, 'down')}><i class="lni lni-chevron-down"></i></button>
                </div>
              </td>
              <td>{l.title}</td>
              <td><a href={l.youtube_url} target="_blank" rel="noreferrer">Link</a></td>
              <td>+{l.release_offset_days}d</td>
              <td>
                <div class="row-actions">
                  <button class="icon-btn" title="Edit lesson" aria-label="Edit lesson" on:click={() => openEditLesson(l)}><i class="lni lni-pencil-1"></i></button>
                  <button class="icon-btn danger" title="Delete lesson" aria-label="Delete lesson" on:click={() => askDelete('lessons', l.id, 'lesson', l.title)}><i class="lni lni-trash-3"></i></button>
                </div>
              </td>
            </tr>
          {:else}
            <tr><td colspan="5" class="empty">No lessons yet.</td></tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else}
    <p class="empty" style="margin-top: 1.5rem;">No modules yet. Add one to start building the course.</p>
  {/each}
  {/if}

  <ConfirmModal
    open={!!confirmTarget}
    title="Delete {confirmTarget?.label}"
    message="Delete “{confirmTarget?.name}”? {confirmTarget?.label === 'module' ? 'Its lessons will be removed with it.' : ''} You can restore it later from the database."
    confirmLabel="Delete"
    danger
    onConfirm={doDelete}
    onClose={() => (confirmTarget = null)}
  />

  <Modal title="Edit Course" open={courseOpen} onClose={() => (courseOpen = false)}>
    <form on:submit|preventDefault={submitCourse}>
      <label for="course-title">Title</label>
      <input id="course-title" bind:value={$courseForm.title} required />

      <label for="course-desc">Description</label>
      <textarea id="course-desc" rows="3" bind:value={$courseForm.description}></textarea>

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (courseOpen = false)}><i class="lni lni-xmark"></i>Cancel</button>
        <button type="submit" disabled={$courseForm.processing}><i class="lni lni-check"></i>Save</button>
      </div>
    </form>
  </Modal>

  <Modal title="Add Module" open={moduleOpen} onClose={() => (moduleOpen = false)}>
    <form on:submit|preventDefault={submitModule}>
      <label for="module-title">Title</label>
      <input id="module-title" bind:value={$moduleForm.title} required />
      <p class="hint">New modules are added to the end. Use the arrows to reorder.</p>

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (moduleOpen = false)}><i class="lni lni-xmark"></i>Cancel</button>
        <button type="submit" disabled={$moduleForm.processing}><i class="lni lni-check"></i>Create</button>
      </div>
    </form>
  </Modal>

  <Modal title="Edit Module" open={moduleEditOpen} onClose={() => (moduleEditOpen = false)}>
    <form on:submit|preventDefault={submitModuleEdit}>
      <label for="module-edit-title">Title</label>
      <input id="module-edit-title" bind:value={$moduleEditForm.title} required />

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (moduleEditOpen = false)}><i class="lni lni-xmark"></i>Cancel</button>
        <button type="submit" disabled={$moduleEditForm.processing}><i class="lni lni-check"></i>Save</button>
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

      <label for="lesson-offset">Days after previous lesson</label>
      <input id="lesson-offset" type="number" min="0" bind:value={$lessonForm.release_offset_days} />
      <p class="hint">Cumulative: 0 = releases with the previous lesson; 7 = one week after it. The first lesson counts from the cohort's start date. New lessons are added to the end — use the arrows to reorder.</p>

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (lessonOpen = false)}><i class="lni lni-xmark"></i>Cancel</button>
        <button type="submit" disabled={$lessonForm.processing}><i class="lni lni-check"></i>Create</button>
      </div>
    </form>
  </Modal>

  <Modal title="Edit Lesson" open={lessonEditOpen} onClose={() => (lessonEditOpen = false)}>
    <form on:submit|preventDefault={submitLessonEdit}>
      <label for="lesson-edit-title">Title</label>
      <input id="lesson-edit-title" bind:value={$lessonEditForm.title} required />

      <label for="lesson-edit-url">YouTube URL</label>
      <input id="lesson-edit-url" type="url" bind:value={$lessonEditForm.youtube_url} required />

      <label for="lesson-edit-desc">Description</label>
      <textarea id="lesson-edit-desc" rows="3" bind:value={$lessonEditForm.description}></textarea>

      <label for="lesson-edit-offset">Days after previous lesson</label>
      <input id="lesson-edit-offset" type="number" min="0" bind:value={$lessonEditForm.release_offset_days} />
      <p class="hint">Cumulative: 0 = releases with the previous lesson; 7 = one week after it. The first lesson counts from the cohort's start date.</p>

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (lessonEditOpen = false)}><i class="lni lni-xmark"></i>Cancel</button>
        <button type="submit" disabled={$lessonEditForm.processing}><i class="lni lni-check"></i>Save</button>
      </div>
    </form>
  </Modal>
</Layout>

<style>
  .title-line { display: flex; align-items: center; gap: 0.4rem; }

  /* Horizontal release timeline: a row of release points connected by an axis
     line, each with a card of the lessons that drop on that day. Scrolls
     sideways when there are more points than fit. */
  .timeline {
    display: flex;
    align-items: flex-start;
    gap: 0;
    overflow-x: auto;
    padding: 0.5rem 0 1rem;
    margin-top: 0.75rem;
  }
  .tl-point {
    flex: 0 0 auto;
    width: 15rem;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  /* The axis line is the top border of each point; adjacent points join it into
     one continuous horizontal line. A dot marks each release. */
  .tl-axis {
    position: relative;
    width: 100%;
    height: 0;
    border-top: 2px solid var(--border);
    margin-top: 0.6rem;
  }
  .tl-point:first-child .tl-axis { margin-left: 50%; width: 50%; }
  .tl-point:last-child .tl-axis { width: 50%; margin-right: 50%; }
  .tl-dot {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 0.7rem;
    height: 0.7rem;
    border-radius: 50%;
    background: var(--accent);
    transform: translate(-50%, -50%);
  }
  .tl-point:first-child .tl-dot { left: 0; }
  .tl-point:last-child .tl-dot { left: 100%; }
  .tl-anchor {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-top: 0.75rem;
  }
  .tl-anchor label { font-weight: 600; font-size: 0.85rem; }
  .tl-anchor input { margin: 0; width: auto; }
  .tl-anchor .hint { margin: 0; }
  .tl-day {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.1rem;
    font-weight: 600;
    font-size: 0.9rem;
    margin: 0.5rem 0 0.6rem;
    text-align: center;
  }
  .tl-offset { font-weight: 400; font-size: 0.72rem; color: var(--muted); }
  .tl-card {
    width: 100%;
    padding: 0 0.4rem;
  }
  .tl-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.4rem;
  }
  .tl-count { font-weight: 600; font-size: 0.85rem; }
  .tl-cumulative { color: var(--muted); font-size: 0.78rem; }
  .tl-lessons { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.35rem; }
  .tl-lessons li {
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--panel);
    padding: 0.4rem 0.55rem;
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }
  .tl-title { font-size: 0.85rem; }
  .tl-module { color: var(--muted); font-size: 0.72rem; }

  .module-card {
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--panel);
    margin-top: 1rem;
    overflow: hidden;
  }
  .module-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.6rem 0.85rem;
    background: #fafafa;
    border-bottom: 1px solid var(--border);
  }
  .module-left { display: flex; align-items: center; gap: 0.5rem; min-width: 0; }
  .module-left h2 { font-size: 1.05rem; }

  .module-card table { margin: 0; }

  /* Stacked up/down reorder arrows as a connected, bordered stepper so they
     read as proper buttons and fit compactly in a cell. */
  .reorder { display: inline-flex; flex-direction: column; }
  .reorder .icon-btn {
    width: 1.7rem;
    height: 1.25rem;
    background: var(--panel);
    color: var(--ink);
    border: 1px solid var(--border);
  }
  .reorder .icon-btn:first-child { border-radius: 6px 6px 0 0; }
  .reorder .icon-btn:last-child { border-radius: 0 0 6px 6px; border-top: 0; }
  .reorder .icon-btn:hover:not(:disabled) { background: #f3f4f6; }
  .reorder .icon-btn .lni { font-size: 0.8em; }
  .reorder .icon-btn:disabled { opacity: 0.4; }
</style>
