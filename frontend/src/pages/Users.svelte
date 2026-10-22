<script>
  import { router, page } from '@inertiajs/svelte'
  import Layout from '../lib/Layout.svelte'
  import Modal from '../lib/Modal.svelte'

  export let users = []

  $: isStaff = $page.props.auth?.user?.is_staff_group
  $: errors = $page.props.errors || {}

  const tabs = [
    { key: 'staff', title: 'Staff', addLabel: 'Add Staff' },
    { key: 'teacher', title: 'Teachers', addLabel: 'Add Teacher' },
    { key: 'trainee', title: 'Trainees', addLabel: 'Add Trainee' },
    { key: 'normal', title: 'Parents', addLabel: null },
  ]

  // Teachers see a flat list (their children's parents + co-teachers), so the
  // role tabs are hidden for them.
  $: showTabs = isStaff

  let active = 'staff'
  let q = ''
  $: activeTab = tabs.find((t) => t.key === active)
  $: needle = q.trim().toLowerCase()
  $: rows = users.filter(
    (u) =>
      (!showTabs || u.role === active) &&
      (!needle ||
        [u.username, u.display_name].some((v) =>
          (v || '').toLowerCase().includes(needle)
        ))
  )

  let open = false
  let processing = false
  let role = 'staff'
  let username = ''
  let full_name = ''
  let password = ''

  function openModal(r) {
    role = r
    username = ''
    full_name = ''
    password = ''
    open = true
  }

  // Mask a trainee's phone to the East Timor (+670) format. Local numbers are
  // 8 digits; drop a leading 670 country code if typed, then group 4-4. The
  // backend strips to digits, so the username stays canonical (670XXXXXXXX).
  function formatTLPhone(value) {
    let digits = String(value || '').replace(/\D/g, '')
    if (digits.startsWith('670')) digits = digits.slice(3)
    digits = digits.slice(0, 8)
    if (!digits) return ''
    const local = digits.length > 4 ? `${digits.slice(0, 4)} ${digits.slice(4)}` : digits
    return `+670 ${local}`
  }
  // Staff and teachers use a plain username + password; trainees are phone-based.
  $: needsPassword = role === 'staff' || role === 'teacher'
  $: isPhone = role === 'trainee'
  function onUsernameInput(e) {
    username = isPhone ? formatTLPhone(e.target.value) : e.target.value
  }

  function submit() {
    processing = true
    router.post(
      '/users/create/',
      { role, username, full_name, password },
      { onSuccess: () => (open = false), onFinish: () => (processing = false) }
    )
  }
</script>

<Layout>
  <div class="page-head">
    <h1>{showTabs ? 'Users' : 'Parents'}</h1>
  </div>

  <div class="toolbar">
    {#if showTabs}
      <div class="seg">
        {#each tabs as t}
          <button class:active={active === t.key} on:click={() => (active = t.key)}>{t.title}</button>
        {/each}
      </div>
    {:else}
      <span></span>
    {/if}
    <div class="toolbar-right">
      <div class="search">
        <i class="lni lni-search-1"></i>
        <input type="search" placeholder="Search {showTabs ? activeTab.title.toLowerCase() : 'users'}…" bind:value={q} />
      </div>
      {#if isStaff && activeTab.addLabel}
        <button on:click={() => openModal(active)}><i class="lni lni-plus"></i>{activeTab.addLabel}</button>
      {/if}
    </div>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        {#if showTabs}
          <tr><th>{active === 'staff' || active === 'teacher' ? 'Username' : 'Phone'}</th><th>Name</th>{#if active === 'trainee'}<th>Cohorts</th>{/if}</tr>
        {:else}
          <tr><th>Name</th><th>Phone</th></tr>
        {/if}
      </thead>
      <tbody>
        {#each rows as u}
          <tr>
            {#if showTabs}
              <td>{u.username}</td>
              <td>{u.display_name || '-'}</td>
              {#if active === 'trainee'}
                <td>
                  {#if u.cohorts && u.cohorts.length}
                    {#each u.cohorts as c, i}<a href={`/elearning/cohorts/${c.id}/`}>{c.name}</a>{#if i < u.cohorts.length - 1}, {/if}{/each}
                  {:else}-{/if}
                </td>
              {/if}
            {:else}
              <td>{u.display_name || '-'}</td>
              <td>{u.username}</td>
            {/if}
          </tr>
        {:else}
          <tr><td colspan={showTabs && active === 'trainee' ? 3 : 2} class="empty">No users to show.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>

  <Modal title={role === 'staff' ? 'Add Staff' : role === 'teacher' ? 'Add Teacher' : 'Add Trainee'} {open} onClose={() => (open = false)}>
    <form on:submit|preventDefault={submit}>
      <label for="username">{isPhone ? 'Phone' : 'Username'}</label>
      <input id="username" type={isPhone ? 'tel' : 'text'} placeholder={isPhone ? '+670 …' : ''} value={username} on:input={onUsernameInput} required />
      {#if errors.username}<p class="error">{errors.username}</p>{/if}

      <label for="full_name">Name</label>
      <input id="full_name" bind:value={full_name} required />

      {#if needsPassword}
        <label for="password">Password</label>
        <input id="password" type="password" bind:value={password} required />
        {#if errors.password}<p class="error">{errors.password}</p>{/if}
      {/if}

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (open = false)}><i class="lni lni-xmark"></i>Cancel</button>
        <button type="submit" disabled={processing}><i class="lni lni-check"></i>Create</button>
      </div>
    </form>
  </Modal>
</Layout>

<style>
  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }
  .toolbar-right { display: flex; align-items: center; gap: 0.75rem; }

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
    width: 240px;
    padding: 0.5rem 0.7rem 0.5rem 2rem;
  }
</style>
