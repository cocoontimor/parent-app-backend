<script>
  import { router, page } from '@inertiajs/svelte'
  import Layout from '../lib/Layout.svelte'
  import Modal from '../lib/Modal.svelte'
  import ConfirmModal from '../lib/ConfirmModal.svelte'
  import MultiSelect from '../lib/MultiSelect.svelte'

  export let circles = []
  export let children = []
  export let users = []
  export let assigned_child_ids = []
  export let graduated = false

  // Creating classes is admin-only; teachers manage the classes they teach.
  $: isAdmin = $page.props.auth?.user?.is_staff_group

  let open = false
  let processing = false
  let editing = null // the circle being edited, or null when creating
  let name = ''
  let teacherIds = []
  let childIds = []

  $: teacherOptions = users.map((u) => ({ value: u.id, label: u.display_name || u.username }))
  $: assignedSet = new Set(assigned_child_ids)
  // A class's own children stay selectable when editing it; everyone else in
  // an active class is hidden.
  $: ownChildren = new Set(editing ? editing.children : [])
  $: childOptions = children
    .filter((c) => !assignedSet.has(c.id) || ownChildren.has(c.id))
    .map((c) => ({ value: c.id, label: c.name }))

  function openModal() {
    editing = null
    name = ''
    teacherIds = []
    childIds = []
    open = true
  }

  function openEdit(c) {
    editing = c
    name = c.name
    teacherIds = [...c.members]
    childIds = [...c.children]
    open = true
  }

  function submit() {
    processing = true
    const url = editing ? `/classes/${editing.id}/edit/` : '/classes/create/'
    router.post(
      url,
      { name, members: teacherIds, children: childIds },
      { onSuccess: () => (open = false), onFinish: () => (processing = false) }
    )
  }

  let expanded = new Set() // ids of classes whose children list is expanded
  function toggleExpand(id) {
    expanded.has(id) ? expanded.delete(id) : expanded.add(id)
    expanded = expanded // trigger reactivity
  }

  let confirmTarget = null // { id, name } of the class pending graduate/restore
  $: confirmVerb = graduated ? 'restore' : 'graduate'

  function toggleGraduate(id, className) {
    confirmTarget = { id, name: className }
  }
  function doToggleGraduate() {
    router.post(`/classes/${confirmTarget.id}/graduate/`, { graduated })
    confirmTarget = null
  }

  const go = (showGraduated) =>
    router.visit(showGraduated ? '/classes/?graduated=1' : '/classes/')
</script>

<Layout>
  <div class="page-head">
    <h1>Classes</h1>
    {#if isAdmin}
      <button on:click={openModal}><i class="lni lni-plus"></i>Add Class</button>
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
        <tr><th>Name</th><th>Teachers</th><th>Children</th><th style="width: 1%;">Actions</th></tr>
      </thead>
      <tbody>
        {#each circles as c}
          <tr>
            <td>{c.name}</td>
            <td>
              {#if c.member_details.length}
                {c.member_details.map((m) => m.name).join(', ')}
              {:else}
                <span class="empty">—</span>
              {/if}
            </td>
            <td>
              {#if c.child_details.length}
                <button class="link-btn" on:click={() => toggleExpand(c.id)}>
                  {c.child_details.length}
                  <i class="lni {expanded.has(c.id) ? 'lni-chevron-up' : 'lni-chevron-down'}"></i>
                </button>
              {:else}
                <span class="empty">0</span>
              {/if}
            </td>
            <td>
              <div class="row-actions">
                {#if !graduated}
                  <button class="icon-btn" title="Attendance" aria-label="Attendance" on:click={() => router.visit(`/classes/${c.id}/attendance/`)}>
                    <i class="lni lni-clipboard"></i>
                  </button>
                  <button class="icon-btn" title="Edit" aria-label="Edit" on:click={() => openEdit(c)}>
                    <i class="lni lni-pencil-1"></i>
                  </button>
                {/if}
                <button class="icon-btn" title={graduated ? 'Restore' : 'Graduate'} aria-label={graduated ? 'Restore' : 'Graduate'} on:click={() => toggleGraduate(c.id, c.name)}>
                  <i class="lni {graduated ? 'lni-refresh-user-1' : 'lni-graduation-cap-1'}"></i>
                </button>
              </div>
            </td>
          </tr>
          {#if expanded.has(c.id)}
            <tr class="child-detail-row">
              <td></td>
              <td colspan="3">
                <ul class="child-list">
                  {#each c.child_details as child}
                    <li>{child.name}</li>
                  {/each}
                </ul>
              </td>
            </tr>
          {/if}
        {:else}
          <tr><td colspan="4" class="empty">No {graduated ? 'graduated' : 'active'} classes.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>

  <ConfirmModal
    open={!!confirmTarget}
    title="{confirmVerb === 'graduate' ? 'Graduate' : 'Restore'} class"
    message="Are you sure you want to {confirmVerb} {confirmTarget?.name}?"
    confirmLabel={confirmVerb === 'graduate' ? 'Graduate' : 'Restore'}
    onConfirm={doToggleGraduate}
    onClose={() => (confirmTarget = null)}
  />

  <Modal title={editing ? 'Edit Class' : 'Add Class'} {open} onClose={() => (open = false)}>
    <form on:submit|preventDefault={submit}>
      <label for="name">Name</label>
      <input id="name" bind:value={name} required />

      <label>Teachers</label>
      <MultiSelect options={teacherOptions} bind:selected={teacherIds} placeholder="Search teachers…" />

      <label>Children</label>
      <MultiSelect options={childOptions} bind:selected={childIds} placeholder="Search children…" />

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (open = false)}><i class="lni lni-xmark"></i>Cancel</button>
        <button type="submit" disabled={processing}><i class="lni lni-check"></i>{editing ? 'Save' : 'Create'}</button>
      </div>
    </form>
  </Modal>
</Layout>

<style>
  .link-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0;
    background: none;
    border: none;
    color: var(--accent, #2563eb);
    cursor: pointer;
    font: inherit;
  }
  .link-btn:hover {
    text-decoration: underline;
  }
  .link-btn .lni {
    font-size: 0.85em;
  }
  .child-detail-row td {
    background: var(--surface-2, rgba(0, 0, 0, 0.02));
  }
  .child-list {
    margin: 0;
    padding: 0.25rem 0 0.25rem 1.25rem;
    columns: 2;
  }
  .child-list li {
    margin: 0.15rem 0;
  }
</style>
