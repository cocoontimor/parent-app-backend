<script>
  import { router } from '@inertiajs/svelte'
  import Layout from '../lib/Layout.svelte'
  import Modal from '../lib/Modal.svelte'
  import MultiSelect from '../lib/MultiSelect.svelte'

  export let circles = []
  export let children = []
  export let users = []
  export let graduated = false

  let open = false
  let processing = false
  let name = ''
  let teacherIds = []
  let childIds = []

  $: teacherOptions = users.map((u) => ({ value: u.id, label: u.display_name || u.username }))
  $: childOptions = children.map((c) => ({ value: c.id, label: c.name }))

  function openModal() {
    name = ''
    teacherIds = []
    childIds = []
    open = true
  }

  function submit() {
    processing = true
    router.post(
      '/classes/create/',
      { name, members: teacherIds, children: childIds },
      { onSuccess: () => (open = false), onFinish: () => (processing = false) }
    )
  }

  function toggleGraduate(id) {
    router.post(`/classes/${id}/graduate/`, { graduated })
  }

  const go = (showGraduated) =>
    router.visit(showGraduated ? '/classes/?graduated=1' : '/classes/')
</script>

<Layout>
  <div class="page-head">
    <h1>Classes</h1>
    <button on:click={openModal}>Add Class</button>
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
        <tr><th>Name</th><th>Teachers</th><th>Children</th><th style="width: 1%;">Actions</th></tr>
      </thead>
      <tbody>
        {#each circles as c}
          <tr>
            <td>{c.name}</td>
            <td>{c.members.length}</td>
            <td>{c.children.length}</td>
            <td>
              <button class="ghost" on:click={() => toggleGraduate(c.id)}>
                {graduated ? 'Restore' : 'Graduate'}
              </button>
            </td>
          </tr>
        {:else}
          <tr><td colspan="4" class="empty">No {graduated ? 'graduated' : 'active'} classes.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>

  <Modal title="Add Class" {open} onClose={() => (open = false)}>
    <form on:submit|preventDefault={submit}>
      <label for="name">Name</label>
      <input id="name" bind:value={name} required />

      <label>Teachers</label>
      <MultiSelect options={teacherOptions} bind:selected={teacherIds} placeholder="Search teachers…" />

      <label>Children</label>
      <MultiSelect options={childOptions} bind:selected={childIds} placeholder="Search children…" />

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (open = false)}>Cancel</button>
        <button type="submit" disabled={processing}>Create</button>
      </div>
    </form>
  </Modal>
</Layout>
