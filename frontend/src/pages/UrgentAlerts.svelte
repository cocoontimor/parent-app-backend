<script>
  import { useForm } from '@inertiajs/svelte'
  import Layout from '../lib/Layout.svelte'
  import Modal from '../lib/Modal.svelte'

  export let alerts = []

  let open = false
  const form = useForm({ title: '', body: '' })

  function submit() {
    if (!confirm('This will immediately notify all parents of non-graduated children. Are you sure?')) return
    $form.post('/urgent-alerts/create/', {
      onSuccess: () => {
        open = false
        $form.reset()
      },
    })
  }

  const fmtDateTime = (v) => new Date(v).toLocaleString()
</script>

<Layout>
  <div class="page-head">
    <h1>Urgent Alerts</h1>
    <button class="danger" on:click={() => (open = true)}>New Alert</button>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Title</th><th>By</th><th>Acknowledged</th><th>Created</th></tr>
      </thead>
      <tbody>
        {#each alerts as a}
          <tr>
            <td>{a.title}</td>
            <td>{a.created_by_name}</td>
            <td>{a.ack_count} / {a.recipient_count}</td>
            <td>{fmtDateTime(a.created)}</td>
          </tr>
        {:else}
          <tr><td colspan="4" class="empty">No urgent alerts yet.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>

  <Modal title="New Urgent Alert" {open} onClose={() => (open = false)}>
    <form on:submit|preventDefault={submit}>
      <label for="title">Title</label>
      <input id="title" bind:value={$form.title} required />

      <label for="body">Message</label>
      <textarea id="body" rows="4" bind:value={$form.body} required></textarea>

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (open = false)}>Cancel</button>
        <button type="submit" class="danger" disabled={$form.processing}>Send</button>
      </div>
    </form>
  </Modal>
</Layout>
