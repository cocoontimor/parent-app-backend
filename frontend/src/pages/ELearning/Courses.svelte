<script>
  import { useForm, router } from '@inertiajs/svelte'
  import Layout from '../../lib/Layout.svelte'
  import Modal from '../../lib/Modal.svelte'

  export let courses = []

  let courseOpen = false

  const courseForm = useForm({ title: '', description: '' })

  function submitCourse() {
    $courseForm.post('/elearning/courses/create/', {
      onSuccess: () => {
        courseOpen = false
        $courseForm.reset()
      },
    })
  }
</script>

<Layout>
  <div class="page-head">
    <h1>Courses</h1>
    <button on:click={() => (courseOpen = true)}><i class="lni lni-plus"></i>New Course</button>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Title</th><th>Modules</th><th>Lessons</th><th style="width: 1%;">Actions</th></tr>
      </thead>
      <tbody>
        {#each courses as c}
          <tr>
            <td>{c.title}</td>
            <td>{c.modules.length}</td>
            <td>{c.lesson_count}</td>
            <td>
              <div class="row-actions">
                <button class="icon-btn" title="View" aria-label="View" on:click={() => router.visit(`/elearning/courses/${c.id}/`)}><i class="lni lni-eye"></i></button>
              </div>
            </td>
          </tr>
        {:else}
          <tr><td colspan="4" class="empty">No courses yet.</td></tr>
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
        <button type="button" class="ghost" on:click={() => (courseOpen = false)}><i class="lni lni-xmark"></i>Cancel</button>
        <button type="submit" disabled={$courseForm.processing}><i class="lni lni-check"></i>Create</button>
      </div>
    </form>
  </Modal>
</Layout>
