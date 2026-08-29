<script>
  import { useForm, router, page } from '@inertiajs/svelte'
  import Layout from '../../lib/Layout.svelte'
  import Modal from '../../lib/Modal.svelte'

  export let announcements = []
  export let circles = []

  $: isStaff = $page.props.auth?.user?.is_staff_group

  let open = false
  const form = useForm({ title: '', body: '', circles: [] })

  function submit() {
    $form.post('/announcements/create/', {
      onSuccess: () => {
        open = false
        $form.reset()
      },
    })
  }

  const fmtDate = (v) => new Date(v).toLocaleDateString()
</script>

<Layout>
  <div class="page-head">
    <h1>Announcements</h1>
    {#if isStaff}
      <button on:click={() => (open = true)}>New Announcement</button>
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
      <input id="title" bind:value={$form.title} required />

      <label for="body">Body</label>
      <textarea id="body" rows="4" bind:value={$form.body} required></textarea>

      <label for="circles">Classes</label>
      <select id="circles" multiple bind:value={$form.circles}>
        {#each circles as c}
          <option value={c.id}>{c.name}</option>
        {/each}
      </select>
      <p class="hint">Leave empty to send to all parents.</p>

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (open = false)}>Cancel</button>
        <button type="submit" disabled={$form.processing}>Create</button>
      </div>
    </form>
  </Modal>
</Layout>
