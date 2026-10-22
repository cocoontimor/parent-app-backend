<script>
  import { router, page } from '@inertiajs/svelte'
  import Layout from '../../lib/Layout.svelte'
  import Modal from '../../lib/Modal.svelte'
  import FilePicker from '../../lib/FilePicker.svelte'

  export let announcements = []
  export let circles = []

  $: isStaff = $page.props.auth?.user?.is_staff_group
  $: isTeacher = $page.props.auth?.user?.is_teacher
  // Teachers may announce to any class, but not to all parents.
  $: canCreate = isStaff || isTeacher

  let open = false
  let title = ''
  let body = ''
  let selectedCircles = []
  let files = []
  let processing = false

  function submit() {
    if (!isStaff && selectedCircles.length === 0) return // teachers must pick a class
    // Build FormData manually so array fields stay as repeated keys the
    // backend reads with getlist(); Inertia's useForm would bracket them.
    const data = new FormData()
    data.append('title', title)
    data.append('body', body)
    for (const id of selectedCircles) data.append('circles', id)
    for (const f of files) data.append('photos', f)

    processing = true
    router.post('/announcements/create/', data, {
      forceFormData: true,
      onSuccess: () => {
        open = false
        title = ''
        body = ''
        selectedCircles = []
        files = []
      },
      onFinish: () => {
        processing = false
      },
    })
  }

  const fmtDate = (v) => new Date(v).toLocaleDateString()
</script>

<Layout>
  <div class="page-head">
    <h1>Announcements</h1>
    {#if canCreate}
      <button on:click={() => (open = true)}><i class="lni lni-plus"></i>New Announcement</button>
    {/if}
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Title</th><th>Acks</th><th>Created</th></tr>
      </thead>
      <tbody>
        {#each announcements as a}
          <tr class="clickable" on:click={() => router.visit(`/announcements/${a.id}/`)}>
            <td>{a.title}</td>
            <td>{a.ack_count}</td>
            <td>{fmtDate(a.created)}</td>
          </tr>
        {:else}
          <tr><td colspan="3" class="empty">No announcements yet.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>

  <Modal title="New Announcement" {open} onClose={() => (open = false)}>
    <form on:submit|preventDefault={submit}>
      <label for="title">Title</label>
      <input id="title" bind:value={title} required />

      <label for="body">Body</label>
      <textarea id="body" rows="4" bind:value={body} required></textarea>

      <label for="circles">Classes</label>
      <select id="circles" multiple bind:value={selectedCircles} required={isTeacher && !isStaff}>
        {#each circles as c}
          <option value={c.id}>{c.name}</option>
        {/each}
      </select>
      {#if isStaff}
        <p class="hint">Leave empty to send to all parents.</p>
      {:else}
        <p class="hint">Select which of your classes to announce to.</p>
      {/if}

      <label>Photos</label>
      <FilePicker bind:files />

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (open = false)}><i class="lni lni-xmark"></i>Cancel</button>
        <button type="submit" disabled={processing}><i class="lni lni-check"></i>Create</button>
      </div>
    </form>
  </Modal>
</Layout>
