<script>
  import { router, page } from '@inertiajs/svelte'
  import Layout from '../../lib/Layout.svelte'
  import Modal from '../../lib/Modal.svelte'

  $: isStaff = $page.props.auth?.user?.is_staff_group
  $: isTeacher = $page.props.auth?.user?.is_teacher
  // Pure parents see only their own child's fees, so the search + month filter
  // add nothing; their list is just sorted by month.
  $: isParent = !isStaff && !isTeacher
  // Staff and teachers can mark receipts off; only admins generate a month.
  $: canMark = isStaff || isTeacher

  export let payments = []
  export let q = ''
  export let month = ''
  export let months = []
  export let status = ''
  export let summary = { total: 0, paid: 0, due: 0, waived: 0, active_amount: 0 }
  export let pagination = { page: 1, num_pages: 1, count: 0, has_previous: false, has_next: false }

  let query = q
  let searchTimer

  // --- Mark a receipt off (paid / waived / revert to pending) ---
  function mark(id, status) {
    router.post(
      `/payments/${id}/mark/`,
      { status, next: $page.url },
      { preserveScroll: true, preserveState: true }
    )
  }

  // --- Admin: generate a month's invoices for all active children ---
  let genOpen = false
  let genMonth = ''
  let genAmount = ''
  let genProcessing = false
  const today = new Date()
  const monthValue = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  const genMonthOptions = Array.from({ length: 9 }, (_, i) => {
    const d = new Date(today.getFullYear(), today.getMonth() - 6 + i, 1)
    return { value: monthValue(d), label: d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' }) }
  })
  function openGenerate() {
    genMonth = monthValue(today)
    genAmount = ''
    genOpen = true
  }
  function submitGenerate() {
    genProcessing = true
    router.post(
      '/payments/generate/',
      { month: genMonth, amount: genAmount || 0 },
      { onSuccess: () => (genOpen = false), onFinish: () => (genProcessing = false) }
    )
  }

  const STATUS = {
    paid: { label: 'Paid', cls: 'paid' },
    pending: { label: 'Due', cls: 'due' },
    waived: { label: 'Waived', cls: 'waived' },
  }

  function reload() {
    router.get('/payments/', { q: query, month, status, page: 1 }, {
      preserveState: true,
      preserveScroll: true,
      replace: true,
    })
  }

  function onSearch() {
    clearTimeout(searchTimer)
    searchTimer = setTimeout(reload, 300)
  }

  function goPage(n) {
    router.get('/payments/', { q: query, month, status, page: n }, { preserveScroll: true })
  }

  const fmtDate = (v) => new Date(v).toLocaleDateString()
  const fmtAmount = (v) =>
    Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  const fmtMonth = (m) =>
    new Date(`${m}-01T00:00:00`).toLocaleDateString(undefined, { year: 'numeric', month: 'long' })
</script>

<Layout>
  <div class="page-head">
    <h1>Payments</h1>
    {#if isStaff}
      <button on:click={openGenerate}><i class="lni lni-plus"></i>Generate month</button>
    {/if}
  </div>

  {#if !isParent}
    <div style="display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 1rem;">
      <div class="summary">
        <strong>{summary.total}</strong> invoice{summary.total === 1 ? '' : 's'}
        · <span class="pay-pill paid">{summary.paid} paid</span>
        · <span class="pay-pill due">{summary.due} due</span>
        {#if summary.waived}· <span class="pay-pill waived">{summary.waived} waived</span>{/if}
        · <strong>{fmtAmount(summary.active_amount)}</strong> from active students
      </div>
      <div style="display: flex; align-items: center; gap: 0.75rem;">
      <select bind:value={status} on:change={reload} style="max-width: 9rem; margin: 0;">
        <option value="">All statuses</option>
        <option value="pending">Due</option>
        <option value="paid">Paid</option>
        <option value="waived">Waived</option>
      </select>
      <select bind:value={month} on:change={reload} style="max-width: 12rem; margin: 0;">
        <option value="">All months</option>
        {#each months as m}
          <option value={m}>{fmtMonth(m)}</option>
        {/each}
      </select>
      <div class="search">
        <i class="lni lni-search-1"></i>
        <input
          type="search"
          placeholder="Search by child or parent"
          bind:value={query}
          on:input={onSearch}
        />
      </div>
      </div>
    </div>
  {/if}

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Child</th>
          {#if !isParent}<th>Parent</th>{/if}
          <th>Month</th>
          <th>Amount</th>
          <th>Status</th>
          {#if canMark}<th style="width: 1%;">Actions</th>{/if}
        </tr>
      </thead>
      <tbody>
        {#each payments as p}
          <tr>
            <td>
              <a href="/children/{p.child}/" on:click|preventDefault={() => router.visit(`/children/${p.child}/`)}>{p.child_name}</a>
            </td>
            {#if !isParent}<td>{(p.parents || []).join(', ') || '-'}</td>{/if}
            <td>{p.month}</td>
            <td>{fmtAmount(p.amount)}</td>
            <td><span class="pay-pill {STATUS[p.status]?.cls}">{STATUS[p.status]?.label || p.status}</span></td>
            {#if canMark}
              <td>
                <div class="row-actions">
                  {#if p.status !== 'paid'}
                    <button class="icon-btn" title="Mark paid" aria-label="Mark paid" on:click={() => mark(p.id, 'paid')}><i class="lni lni-check"></i></button>
                  {/if}
                  {#if p.status !== 'waived'}
                    <button class="icon-btn ghost" title="Waive" aria-label="Waive" on:click={() => mark(p.id, 'waived')}><i class="lni lni-ban-2"></i></button>
                  {/if}
                  {#if p.status !== 'pending'}
                    <button class="icon-btn ghost" title="Mark unpaid" aria-label="Mark unpaid" on:click={() => mark(p.id, 'pending')}><i class="lni lni-refresh-circle-1-clockwise"></i></button>
                  {/if}
                </div>
              </td>
            {/if}
          </tr>
        {:else}
          <tr><td colspan={(!isParent ? 5 : 4) + (canMark ? 1 : 0)} class="empty">
            {#if q}No payments match "{q}".{:else}No payments yet.{/if}
          </td></tr>
        {/each}
      </tbody>
    </table>
  </div>

  <Modal title="Generate monthly invoices" open={genOpen} onClose={() => (genOpen = false)}>
    <form on:submit|preventDefault={submitGenerate}>
      <label for="gen-month">Month</label>
      <select id="gen-month" bind:value={genMonth} required>
        {#each genMonthOptions as m}
          <option value={m.value}>{m.label}</option>
        {/each}
      </select>

      <label for="gen-amount">Amount per child</label>
      <input id="gen-amount" inputmode="decimal" placeholder="0.00" bind:value={genAmount} required />
      <p class="hint">Creates a “Due” invoice for every active child that doesn’t already have one for this month. Existing rows are left untouched.</p>

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (genOpen = false)}><i class="lni lni-xmark"></i>Cancel</button>
        <button type="submit" disabled={genProcessing}><i class="lni lni-check"></i>Generate</button>
      </div>
    </form>
  </Modal>

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
</Layout>

<style>
  .pay-pill {
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    background: #f1f5f9;
    color: var(--muted);
  }
  .pay-pill.paid { background: #dcfce7; color: #16a34a; }
  .pay-pill.due { background: #fee2e2; color: #dc2626; }
  .pay-pill.waived { background: #e0e7ff; color: #4f46e5; }

  .summary { color: var(--muted); font-size: 0.9rem; display: flex; align-items: center; gap: 0.35rem; flex-wrap: wrap; }
  .summary strong { color: var(--ink); }

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
