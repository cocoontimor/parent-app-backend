<script>
  import { router, page } from '@inertiajs/svelte'
  import Layout from '../lib/Layout.svelte'
  import Modal from '../lib/Modal.svelte'

  export let children = []
  export let graduated = false

  $: isStaff = $page.props.auth?.user?.is_staff_group

  const MAX_PARENTS = 4
  const relationships = [
    { value: 'mother', label: 'Mother' },
    { value: 'father', label: 'Father' },
    { value: 'guardian', label: 'Guardian' },
    { value: 'other', label: 'Other' },
  ]

  let open = false
  let processing = false
  let name = ''
  let dob = ''
  let parents = []

  function newParent() {
    return { full_name: '', relationship: 'mother', number: '' }
  }
  function openModal() {
    name = ''
    dob = ''
    parents = [newParent()]
    open = true
  }
  function addParent() {
    if (parents.length < MAX_PARENTS) parents = [...parents, newParent()]
  }
  function removeParent(i) {
    parents = parents.filter((_, idx) => idx !== i)
  }

  function submit() {
    processing = true
    router.post(
      '/children/create/',
      { name, date_of_birth: dob || null, parents },
      {
        onSuccess: () => (open = false),
        onFinish: () => (processing = false),
      }
    )
  }

  function toggleGraduate(id) {
    router.post(`/children/${id}/graduate/`, { graduated })
  }

  const go = (showGraduated) =>
    router.visit(showGraduated ? '/children/?graduated=1' : '/children/')

  const fmtDate = (v) => (v ? new Date(v).toLocaleDateString() : '-')
</script>

<Layout>
  <div class="page-head">
    <h1>Children</h1>
    {#if isStaff}
      <button on:click={openModal}>Add Child</button>
    {/if}
  </div>

  <div style="margin-bottom: 1rem;">
    <div class="seg">
      <button class:active={!graduated} on:click={() => go(false)}>Active</button>
      <button class:active={graduated} on:click={() => go(true)}>Graduated</button>
    </div>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Name</th><th>Date of Birth</th><th>Created</th><th style="width: 1%;">Actions</th></tr>
      </thead>
      <tbody>
        {#each children as c}
          <tr>
            <td>{c.name}</td>
            <td>{c.date_of_birth || '-'}</td>
            <td>{fmtDate(c.created)}</td>
            <td style="white-space: nowrap;">
              <button class="ghost" on:click={() => router.visit(`/children/${c.id}/`)}>View</button>
              {#if isStaff}
                <button class="ghost" on:click={() => toggleGraduate(c.id)}>
                  {graduated ? 'Restore' : 'Graduate'}
                </button>
              {/if}
            </td>
          </tr>
        {:else}
          <tr><td colspan="4" class="empty">No {graduated ? 'graduated' : 'active'} children.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>

  <Modal title="Add Child" {open} onClose={() => (open = false)}>
    <form on:submit|preventDefault={submit}>
      <label for="name">Name</label>
      <input id="name" bind:value={name} required />

      <label for="dob">Date of Birth</label>
      <input id="dob" type="date" bind:value={dob} />

      <div style="display: flex; justify-content: space-between; align-items: center; margin: 0.5rem 0 0.75rem;">
        <strong style="font-size: 0.9rem;">Parents</strong>
        <button type="button" class="ghost" on:click={addParent} disabled={parents.length >= MAX_PARENTS}>
          + Add Parent
        </button>
      </div>

      {#each parents as p, i (i)}
        <div style="border: 1px solid var(--border); border-radius: 8px; padding: 0.75rem; margin-bottom: 0.75rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <span style="color: var(--muted); font-size: 0.8rem;">Parent {i + 1}</span>
            <button type="button" class="ghost" style="padding: 0.1rem 0.5rem;" on:click={() => removeParent(i)}>✕</button>
          </div>
          <input placeholder="Full name" bind:value={p.full_name} style="margin-bottom: 0.5rem;" />
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
            <select bind:value={p.relationship}>
              {#each relationships as r}
                <option value={r.value}>{r.label}</option>
              {/each}
            </select>
            <input type="tel" placeholder="Phone number" bind:value={p.number} />
          </div>
        </div>
      {/each}

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (open = false)}>Cancel</button>
        <button type="submit" disabled={processing}>Create</button>
      </div>
    </form>
  </Modal>
</Layout>
