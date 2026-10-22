<script>
  import { router, page } from '@inertiajs/svelte'
  import Layout from '../lib/Layout.svelte'
  import Modal from '../lib/Modal.svelte'
  import ConfirmModal from '../lib/ConfirmModal.svelte'

  export let children = []
  export let graduated = false
  export let q = ''
  export let pagination = { page: 1, num_pages: 1, count: 0, has_previous: false, has_next: false }

  // Add Child is admin-only; graduating is allowed for teachers too (they only
  // see their own class's children here).
  $: isStaff = $page.props.auth?.user?.is_staff_group
  $: canManage = isStaff || $page.props.auth?.user?.is_teacher

  const MAX_PARENTS = 4
  const relationships = [
    { value: 'mother', label: 'Mother' },
    { value: 'father', label: 'Father' },
    { value: 'guardian', label: 'Guardian' },
    { value: 'other', label: 'Other' },
  ]

  let query = q
  let searchTimer

  // Build the query string, always carrying the active/graduated tab.
  function params(extra) {
    const p = { ...extra }
    if (graduated) p.graduated = 1
    if (!p.q) delete p.q
    return p
  }

  function onSearch() {
    clearTimeout(searchTimer)
    searchTimer = setTimeout(() => {
      router.get('/children/', params({ q: query, page: 1 }), {
        preserveState: true,
        preserveScroll: true,
        replace: true,
      })
    }, 300)
  }

  function goPage(n) {
    router.get('/children/', params({ q: query, page: n }), {
      preserveScroll: true,
    })
  }

  let open = false
  let processing = false
  let name = ''
  let dob = ''
  let parents = []

  function newParent() {
    return { full_name: '', relationship: 'mother', number: '' }
  }

  // Mask parent phone numbers to the East Timor (+670) format. Local numbers
  // are 8 digits; drop a leading 670 country code if typed, then group 4-4.
  // The backend strips to digits, so the username stays canonical (670XXXXXXXX).
  function formatTLPhone(value) {
    let digits = String(value || '').replace(/\D/g, '')
    if (digits.startsWith('670')) digits = digits.slice(3)
    digits = digits.slice(0, 8)
    if (!digits) return ''
    const local = digits.length > 4 ? `${digits.slice(0, 4)} ${digits.slice(4)}` : digits
    return `+670 ${local}`
  }
  function onNumberInput(i, e) {
    const formatted = formatTLPhone(e.target.value)
    parents = parents.map((p, idx) => (idx === i ? { ...p, number: formatted } : p))
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

  let confirmTarget = null // { id, name } of the child pending graduate/restore
  $: confirmVerb = graduated ? 'restore' : 'graduate'

  function toggleGraduate(id, childName) {
    confirmTarget = { id, name: childName }
  }
  function doToggleGraduate() {
    router.post(`/children/${confirmTarget.id}/graduate/`, { graduated })
    confirmTarget = null
  }

  const go = (showGraduated) =>
    router.visit(showGraduated ? '/children/?graduated=1' : '/children/')

  const fmtDate = (v) => (v ? new Date(v).toLocaleDateString() : '-')
</script>

<Layout>
  <div class="page-head">
    <h1>Children</h1>
    {#if isStaff}
      <button on:click={openModal}><i class="lni lni-plus"></i>Add Child</button>
    {/if}
  </div>

  <div style="display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin-bottom: 1rem;">
    <div class="seg">
      <button class:active={!graduated} on:click={() => go(false)}>Active</button>
      <button class:active={graduated} on:click={() => go(true)}>Graduated</button>
    </div>
    <div class="search">
      <i class="lni lni-search-1"></i>
      <input
        type="search"
        placeholder="Search by name, parent, or class"
        bind:value={query}
        on:input={onSearch}
      />
    </div>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Name</th><th>Parents</th><th>Class</th><th>Date of Birth</th><th>Created</th><th style="width: 1%;">Actions</th></tr>
      </thead>
      <tbody>
        {#each children as c}
          <tr>
            <td>{c.name}</td>
            <td>{(c.parents || []).join(', ') || '-'}</td>
            <td>{(c.classes || []).join(', ') || '-'}</td>
            <td>{c.date_of_birth || '-'}</td>
            <td>{fmtDate(c.created)}</td>
            <td>
              <div class="row-actions">
                <button class="icon-btn" title="View" aria-label="View" on:click={() => router.visit(`/children/${c.id}/`)}><i class="lni lni-eye"></i></button>
                {#if canManage}
                  <button class="icon-btn" title={graduated ? 'Restore' : 'Graduate'} aria-label={graduated ? 'Restore' : 'Graduate'} on:click={() => toggleGraduate(c.id, c.name)}>
                    <i class="lni {graduated ? 'lni-refresh-user-1' : 'lni-graduation-cap-1'}"></i>
                  </button>
                {/if}
              </div>
            </td>
          </tr>
        {:else}
          <tr><td colspan="6" class="empty">
            {#if q}No children match "{q}".{:else}No {graduated ? 'graduated' : 'active'} children.{/if}
          </td></tr>
        {/each}
      </tbody>
    </table>
  </div>

  {#if pagination.num_pages > 1}
    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem;">
      <span style="color: var(--muted); font-size: 0.85rem;">
        Page {pagination.page} of {pagination.num_pages} · {pagination.count} total
      </span>
      <div class="seg">
        <button disabled={!pagination.has_previous} on:click={() => goPage(pagination.page - 1)}><i class="lni lni-chevron-left"></i>Prev</button>
        <button disabled={!pagination.has_next} on:click={() => goPage(pagination.page + 1)}>Next<i class="lni lni-chevron-right"></i></button>
      </div>
    </div>
  {/if}

  <ConfirmModal
    open={!!confirmTarget}
    title="{confirmVerb === 'graduate' ? 'Graduate' : 'Restore'} child"
    message="Are you sure you want to {confirmVerb} {confirmTarget?.name}?"
    confirmLabel={confirmVerb === 'graduate' ? 'Graduate' : 'Restore'}
    onConfirm={doToggleGraduate}
    onClose={() => (confirmTarget = null)}
  />

  <Modal title="Add Child" {open} onClose={() => (open = false)}>
    <form on:submit|preventDefault={submit}>
      <label for="name">Name</label>
      <input id="name" bind:value={name} required />

      <label for="dob">Date of Birth</label>
      <input id="dob" type="date" bind:value={dob} />

      <div style="display: flex; justify-content: space-between; align-items: center; margin: 0.5rem 0 0.75rem;">
        <strong style="font-size: 0.9rem;">Parents</strong>
        <button type="button" class="ghost" on:click={addParent} disabled={parents.length >= MAX_PARENTS}>
          <i class="lni lni-plus"></i>Add Parent
        </button>
      </div>

      {#each parents as p, i (i)}
        <div style="border: 1px solid var(--border); border-radius: 8px; padding: 0.75rem; margin-bottom: 0.75rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <span style="color: var(--muted); font-size: 0.8rem;">Parent {i + 1}</span>
            <button type="button" class="ghost" style="padding: 0.1rem 0.5rem;" aria-label="Remove parent" on:click={() => removeParent(i)}><i class="lni lni-xmark"></i></button>
          </div>
          <input placeholder="Full name" bind:value={p.full_name} style="margin-bottom: 0.5rem;" />
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
            <select bind:value={p.relationship}>
              {#each relationships as r}
                <option value={r.value}>{r.label}</option>
              {/each}
            </select>
            <input type="tel" placeholder="+670 …" value={p.number} on:input={(e) => onNumberInput(i, e)} />
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

<style>
  .search { position: relative; display: flex; align-items: center; }
  .search .lni {
    position: absolute;
    left: 0.6rem;
    color: var(--muted);
    font-size: 0.95em;
    pointer-events: none;
  }
  .search input {
    margin: 0;
    width: 20rem;
    max-width: 100%;
    padding: 0.5rem 0.7rem 0.5rem 2rem;
  }
</style>
