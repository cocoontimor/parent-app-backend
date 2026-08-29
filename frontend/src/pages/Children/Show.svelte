<script>
  import { useForm, inertia, page } from '@inertiajs/svelte'
  import Layout from '../../lib/Layout.svelte'
  import Modal from '../../lib/Modal.svelte'

  export let child
  export let classes = []
  export let updates = []

  $: isStaff = $page.props.auth?.user?.is_staff_group

  let open = false
  const form = useForm({ child: child.id, text: '' })

  function submit() {
    $form.post('/updates/create/', {
      onSuccess: () => {
        open = false
        $form.reset('text')
      },
    })
  }

  const fmtDate = (v) => new Date(v).toLocaleDateString()
  const fmtDateTime = (v) => new Date(v).toLocaleString()
</script>

<Layout>
  <div class="page-head">
    <h1>{child.name}</h1>
    <a href="/children/" use:inertia><button class="ghost">← Back</button></a>
  </div>

  <div class="card" style="margin-bottom: 1rem;">
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
      <div><span style="color: var(--muted);">Date of Birth:</span> {child.date_of_birth || '-'}</div>
      <div><span style="color: var(--muted);">Added:</span> {fmtDate(child.created)}</div>
    </div>
  </div>

  <div class="card" style="margin-bottom: 1rem;">
    <h3 style="margin-bottom: 1rem;">Classes</h3>
    {#if classes.length === 0}
      <p style="color: var(--muted); margin: 0;">Not in any class yet.</p>
    {:else}
      {#each classes as k}
        <div style="padding: 0.6rem 0; border-bottom: 1px solid var(--border);">
          <div>
            <strong>{k.name}</strong>
            <span class="tag {k.type === 'family' ? 'blue' : 'green'}" style="margin-left: 0.5rem;">{k.type}</span>
          </div>
          <div style="color: var(--muted); font-size: 0.85rem; margin-top: 0.25rem;">
            Parents: {k.parents.length
              ? k.parents.map((p) => (p.relationship ? `${p.name} (${p.relationship})` : p.name)).join(', ')
              : 'none'}
          </div>
        </div>
      {/each}
    {/if}
  </div>

  <div class="card">
    <div class="page-head">
      <h3>Updates</h3>
      {#if isStaff}
        <button on:click={() => (open = true)}>New Update</button>
      {/if}
    </div>
    <div class="table-wrap" style="border: 0;">
      <table>
        <thead>
          <tr><th>Text</th><th>By</th><th>Created</th></tr>
        </thead>
        <tbody>
          {#each updates as u}
            <tr>
              <td>{u.text}</td>
              <td>{u.created_by_name}</td>
              <td>{fmtDateTime(u.created)}</td>
            </tr>
          {:else}
            <tr><td colspan="3" class="empty">No updates yet.</td></tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>

  <Modal title="New Update for {child.name}" {open} onClose={() => (open = false)}>
    <form on:submit|preventDefault={submit}>
      <label for="text">Update Text</label>
      <textarea id="text" rows="4" bind:value={$form.text} required></textarea>

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (open = false)}>Cancel</button>
        <button type="submit" disabled={$form.processing}>Create</button>
      </div>
    </form>
  </Modal>
</Layout>
