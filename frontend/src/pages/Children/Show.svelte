<script>
  import { router, inertia, page } from '@inertiajs/svelte'
  import Layout from '../../lib/Layout.svelte'
  import Modal from '../../lib/Modal.svelte'
  import FilePicker from '../../lib/FilePicker.svelte'

  export let child
  export let family = null
  export let classes = []
  export let updates = []
  export let payments = []
  export let attendance = []
  export let attendance_pagination = { page: 1, num_pages: 1, count: 0, has_previous: false, has_next: false }

  // The page only loads for children in scope, so staff or a teacher of this
  // child's class may manage it.
  $: isStaff = $page.props.auth?.user?.is_staff_group || $page.props.auth?.user?.is_teacher

  const MAX_PARENTS = 4
  const relationships = [
    { value: 'mother', label: 'Mother' },
    { value: 'father', label: 'Father' },
    { value: 'guardian', label: 'Guardian' },
    { value: 'other', label: 'Other' },
  ]

  let open = false
  let text = ''
  let files = []
  let processing = false

  let editOpen = false
  let editName = ''
  let editDob = ''
  let editProcessing = false

  let familyOpen = false
  let familyProcessing = false
  let parents = []
  let parentQuery = ''
  let parentResults = []
  let parentSearchTimer

  const newParent = () => ({ full_name: '', relationship: 'mother', number: '', locked: false })

  // Canonical 8-digit local part (drops the +670 country code) so we can tell
  // whether an existing parent is already among the current rows.
  const localKey = (v) => {
    let d = String(v || '').replace(/\D/g, '')
    if (d.startsWith('670')) d = d.slice(3)
    return d.slice(0, 8)
  }

  // Debounced server-side search over existing parent accounts. Results that
  // are already listed in the form are filtered out client-side.
  $: usedKeys = new Set(parents.map((p) => localKey(p.number)))
  $: parentMatches = parentResults.filter((u) => !usedKeys.has(localKey(u.number)))

  function onParentSearch() {
    clearTimeout(parentSearchTimer)
    const q = parentQuery.trim()
    if (!q) {
      parentResults = []
      return
    }
    parentSearchTimer = setTimeout(async () => {
      try {
        const res = await fetch(`/parents/search/?q=${encodeURIComponent(q)}`, {
          headers: { Accept: 'application/json' },
        })
        parentResults = res.ok ? (await res.json()).parents : []
      } catch {
        parentResults = []
      }
    }, 250)
  }

  function pickParent(u) {
    if (parents.length >= MAX_PARENTS) return
    parents = [
      ...parents,
      { full_name: u.full_name || '', relationship: 'mother', number: formatTLPhone(u.number), locked: true },
    ]
    parentQuery = ''
    parentResults = []
  }

  // Mask parent phone numbers to the East Timor (+670) format. Local numbers
  // are 8 digits; we drop a leading 670 country code if the user includes it,
  // then group the local part 4-4. Returns "" when there are no digits so the
  // field can be cleared. The backend strips everything but digits, so the
  // stored username is always the canonical 670XXXXXXXX (keeps dedup stable).
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

  function openFamily() {
    parentQuery = ''
    parentResults = []
    parents = family && family.parents.length
      ? family.parents.map((p) => ({
          full_name: p.full_name || '',
          relationship: relationships.some((r) => r.value === p.relationship) ? p.relationship : 'other',
          number: formatTLPhone(p.number),
          locked: false,
        }))
      : [newParent()]
    familyOpen = true
  }
  function addParent() {
    if (parents.length < MAX_PARENTS) parents = [...parents, newParent()]
  }
  function removeParent(i) {
    parents = parents.filter((_, idx) => idx !== i)
  }
  function submitFamily() {
    familyProcessing = true
    router.post(
      `/children/${child.id}/family/`,
      { parents },
      {
        onSuccess: () => (familyOpen = false),
        onFinish: () => (familyProcessing = false),
      }
    )
  }

  function openEdit() {
    editName = child.name
    editDob = child.date_of_birth || ''
    editOpen = true
  }

  function submitEdit() {
    editProcessing = true
    router.post(
      `/children/${child.id}/edit/`,
      { name: editName, date_of_birth: editDob || null },
      {
        onSuccess: () => (editOpen = false),
        onFinish: () => (editProcessing = false),
      }
    )
  }

  function submit() {
    const data = new FormData()
    data.append('child', child.id)
    data.append('text', text)
    for (const f of files) data.append('photos', f)

    processing = true
    router.post('/updates/create/', data, {
      forceFormData: true,
      onSuccess: () => {
        open = false
        text = ''
        files = []
      },
      onFinish: () => {
        processing = false
      },
    })
  }

  const fmtDate = (v) => new Date(v).toLocaleDateString()
  const fmtDateTime = (v) => new Date(v).toLocaleString()
  const fmtAmount = (v) =>
    Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

  // Month dropdown: 6 months back through 2 months forward from today.
  const today = new Date()
  const monthValue = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  const monthOptions = Array.from({ length: 9 }, (_, i) => {
    const d = new Date(today.getFullYear(), today.getMonth() - 6 + i, 1)
    return { value: monthValue(d), label: d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' }) }
  })

  let activeTab = 'updates' // 'updates' | 'payments' | 'attendance'

  // Attendance is paginated on its own ?att_page=; preserveState keeps the tab.
  function goAttPage(n) {
    router.get(`/children/${child.id}/`, { att_page: n }, {
      preserveState: true,
      preserveScroll: true,
    })
  }

  let payOpen = false
  let payProcessing = false
  let payMonth = ''
  let payAmount = '' // raw numeric string sent to the server
  let payAmountDisplay = '' // masked value shown in the input

  function openPay() {
    payMonth = monthValue(today)
    payAmount = ''
    payAmountDisplay = ''
    payOpen = true
  }

  // Mask the amount: keep digits and one decimal point, cap decimals at 2, and
  // group thousands as the user types.
  function onAmountInput(e) {
    const raw = e.target.value.replace(/[^\d.]/g, '')
    const dot = raw.indexOf('.')
    let intPart = (dot === -1 ? raw : raw.slice(0, dot)).replace(/^0+(?=\d)/, '')
    const decPart = dot === -1 ? null : raw.slice(dot + 1).replace(/\./g, '').slice(0, 2)
    const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
    payAmountDisplay = decPart === null ? grouped : `${grouped}.${decPart}`
    payAmount = payAmountDisplay.replace(/,/g, '')
  }

  function onAmountBlur() {
    const n = parseFloat(payAmountDisplay.replace(/,/g, ''))
    if (isNaN(n)) {
      payAmountDisplay = ''
      payAmount = ''
      return
    }
    payAmountDisplay = fmtAmount(n)
    payAmount = String(n)
  }

  function submitPay() {
    payProcessing = true
    router.post(
      '/payments/create/',
      { child: child.id, month: payMonth, amount: payAmount },
      {
        onSuccess: () => (payOpen = false),
        onFinish: () => (payProcessing = false),
      }
    )
  }

  // Staff send the WhatsApp receipt to the child's parents on demand, per
  // payment row, via the confirmation modal.
  let confirming = null

  function openConfirm(p) {
    confirming = p
  }

  function sendConfirmation() {
    router.post(`/payments/${confirming.id}/send-confirmation/`, {}, {
      preserveScroll: true,
      onFinish: () => (confirming = null),
    })
  }

  function dismissConfirm() {
    confirming = null
  }

  const PAY_STATUS = {
    paid: { label: 'Paid', cls: 'paid' },
    pending: { label: 'Due', cls: 'due' },
    waived: { label: 'Waived', cls: 'waived' },
  }
  function markPayment(id, status) {
    router.post(
      `/payments/${id}/mark/`,
      { status, next: `/children/${child.id}/` },
      { preserveScroll: true, preserveState: true }
    )
  }
</script>

<Layout>
  <div class="page-head">
    <h1>{child.name}</h1>
    <a href="/children/" use:inertia><button class="ghost"><i class="lni lni-arrow-left"></i>Back</button></a>
  </div>

  <div class="card" style="margin-bottom: 1rem; display: flex; align-items: center; gap: 0.75rem;">
    <div style="flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
      <div><span style="color: var(--muted);">Date of Birth:</span> {child.date_of_birth || '-'}</div>
      <div><span style="color: var(--muted);">Added:</span> {fmtDate(child.created)}</div>
    </div>
    {#if isStaff}
      <button class="icon-btn" title="Edit" aria-label="Edit" on:click={openEdit}><i class="lni lni-pencil-1"></i></button>
    {/if}
  </div>

  <div class="card" style="margin-bottom: 1rem;">
    <div class="page-head">
      <h3>Family</h3>
      {#if isStaff}
        <button class="card-action" on:click={openFamily}>
          <i class="lni {family && family.parents.length ? 'lni-pencil-1' : 'lni-plus'}"></i>
          {family && family.parents.length ? 'Edit Family' : 'Add Family'}
        </button>
      {/if}
    </div>
    {#if !family || family.parents.length === 0}
      <p style="color: var(--muted); margin: 0;">No family members yet.</p>
    {:else}
      {#each family.parents as p}
        <div style="padding: 0.6rem 0; border-bottom: 1px solid var(--border);">
          <div>
            <strong>{p.name}</strong>
            {#if p.relationship}
              <span class="tag blue" style="margin-left: 0.5rem;">{p.relationship}</span>
            {/if}
          </div>
          <div style="color: var(--muted); font-size: 0.85rem; margin-top: 0.25rem;">{p.number}</div>
        </div>
      {/each}
    {/if}
  </div>

  <div class="card" style="margin-bottom: 1rem;">
    <h3 style="margin-bottom: 1rem;">Classes</h3>
    {#if classes.length === 0}
      <p style="color: var(--muted); margin: 0;">Not in any class yet.</p>
    {:else}
      {#each classes as k}
        <div style="padding: 0.6rem 0; border-bottom: 1px solid var(--border);">
          <strong>{k.name}</strong>
          <div style="color: var(--muted); font-size: 0.85rem; margin-top: 0.25rem;">
            Teachers: {k.teachers.length ? k.teachers.join(', ') : 'none'}
          </div>
        </div>
      {/each}
    {/if}
  </div>

  <div class="seg tabs" style="margin-bottom: 0.75rem;">
    <button class:active={activeTab === 'updates'} on:click={() => (activeTab = 'updates')}>Updates</button>
    <button class:active={activeTab === 'payments'} on:click={() => (activeTab = 'payments')}>Payments</button>
    <button class:active={activeTab === 'attendance'} on:click={() => (activeTab = 'attendance')}>Attendance</button>
  </div>

  <div class="card">
    {#if isStaff && activeTab !== 'attendance'}
      <div class="card-head">
        {#if activeTab === 'payments'}
          <button on:click={openPay}><i class="lni lni-plus"></i>Add Payment</button>
        {:else}
          <button on:click={() => (open = true)}><i class="lni lni-plus"></i>Add Update</button>
        {/if}
      </div>
    {/if}

    {#if activeTab === 'payments'}
      <div class="table-wrap" style="border: 0;">
        <table>
          <thead>
            <tr><th>Month</th><th>Amount</th><th>Status</th>{#if isStaff}<th style="width: 1%;"></th>{/if}</tr>
          </thead>
          <tbody>
            {#each payments as p}
              <tr>
                <td>{p.month}</td>
                <td>{fmtAmount(p.amount)}</td>
                <td><span class="pay-pill {PAY_STATUS[p.status]?.cls}">{PAY_STATUS[p.status]?.label || p.status}</span></td>
                {#if isStaff}
                  <td>
                    <div class="row-actions" style="justify-content: flex-end;">
                      {#if p.status !== 'paid'}
                        <button class="icon-btn" title="Mark paid" aria-label="Mark paid" on:click={() => markPayment(p.id, 'paid')}><i class="lni lni-check"></i></button>
                      {/if}
                      {#if p.status !== 'waived'}
                        <button class="icon-btn ghost" title="Waive" aria-label="Waive" on:click={() => markPayment(p.id, 'waived')}><i class="lni lni-ban-2"></i></button>
                      {/if}
                      {#if p.status !== 'pending'}
                        <button class="icon-btn ghost" title="Mark unpaid" aria-label="Mark unpaid" on:click={() => markPayment(p.id, 'pending')}><i class="lni lni-refresh-circle-1-clockwise"></i></button>
                      {/if}
                      {#if p.status === 'paid'}
                        <button class="icon-btn" title="Send receipt" aria-label="Send receipt" on:click={() => openConfirm(p)}><i class="lni lni-telegram"></i></button>
                      {/if}
                    </div>
                  </td>
                {/if}
              </tr>
            {:else}
              <tr><td colspan={isStaff ? 4 : 3} class="empty">No payments yet.</td></tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else if activeTab === 'attendance'}
      <div class="table-wrap" style="border: 0;">
        <table>
          <thead>
            <tr><th>Date</th><th>Status</th></tr>
          </thead>
          <tbody>
            {#each attendance as a}
              <tr>
                <td>{fmtDate(a.date)}</td>
                <td>
                  <span class="att-pill {a.status}">{a.status === 'present' ? 'Present' : 'Absent'}</span>
                </td>
              </tr>
            {:else}
              <tr><td colspan="2" class="empty">No attendance recorded yet.</td></tr>
            {/each}
          </tbody>
        </table>
      </div>
      {#if attendance_pagination.num_pages > 1}
        <div class="att-pager">
          <span class="hint" style="margin: 0;">
            Page {attendance_pagination.page} of {attendance_pagination.num_pages} · {attendance_pagination.count} total
          </span>
          <div class="seg">
            <button disabled={!attendance_pagination.has_previous} on:click={() => goAttPage(attendance_pagination.page - 1)}><i class="lni lni-chevron-left"></i>Prev</button>
            <button disabled={!attendance_pagination.has_next} on:click={() => goAttPage(attendance_pagination.page + 1)}>Next<i class="lni lni-chevron-right"></i></button>
          </div>
        </div>
      {/if}
    {:else}
      <div class="table-wrap" style="border: 0;">
        <table>
          <thead>
            <tr><th>Text</th><th>By</th><th>Created</th></tr>
          </thead>
          <tbody>
            {#each updates as u}
              <tr>
                <td>
                  {u.text}
                  {#if u.photos?.length}
                    <div style="display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.4rem;">
                      {#each u.photos as p}
                        <a href={p.image} target="_blank" rel="noopener">
                          <img src={p.image} alt="" style="height: 56px; border-radius: 4px; object-fit: cover;" />
                        </a>
                      {/each}
                    </div>
                  {/if}
                </td>
                <td>{u.created_by_name}</td>
                <td>{fmtDateTime(u.created)}</td>
              </tr>
            {:else}
              <tr><td colspan="3" class="empty">No updates yet.</td></tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>

  <Modal title="{family && family.parents.length ? 'Edit' : 'Add'} Family" open={familyOpen} onClose={() => (familyOpen = false)}>
    <form on:submit|preventDefault={submitFamily}>
      <div style="display: flex; justify-content: space-between; align-items: center; margin: 0 0 0.75rem;">
        <strong style="font-size: 0.9rem;">Parents</strong>
        <button type="button" class="ghost" on:click={addParent} disabled={parents.length >= MAX_PARENTS}>
          <i class="lni lni-plus"></i>Add Parent
        </button>
      </div>

      {#if parents.length < MAX_PARENTS}
        <div style="position: relative; margin-bottom: 0.75rem;">
          <input placeholder="Find existing parent…" bind:value={parentQuery} on:input={onParentSearch} style="margin: 0;" />
          {#if parentQuery.trim()}
            <div class="parent-picker">
              {#each parentMatches as u}
                <button type="button" class="parent-option" on:click={() => pickParent(u)}>
                  <span>{u.full_name || '(no name)'}</span>
                  <span style="color: var(--muted); font-size: 0.85rem;">{formatTLPhone(u.number)}</span>
                </button>
              {:else}
                <div style="padding: 0.5rem 0.6rem; color: var(--muted); font-size: 0.85rem;">No matches</div>
              {/each}
            </div>
          {/if}
        </div>
      {/if}

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
            {#if p.locked}
              <input type="tel" value={p.number} readonly title="Existing parent account" class="locked-num" />
            {:else}
              <input type="tel" placeholder="+670 …" value={p.number} on:input={(e) => onNumberInput(i, e)} />
            {/if}
          </div>
        </div>
      {/each}

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (familyOpen = false)}><i class="lni lni-xmark"></i>Cancel</button>
        <button type="submit" disabled={familyProcessing}><i class="lni lni-check"></i>Save</button>
      </div>
    </form>
  </Modal>

  <Modal title="Edit Child" open={editOpen} onClose={() => (editOpen = false)}>
    <form on:submit|preventDefault={submitEdit}>
      <label for="edit-name">Name</label>
      <input id="edit-name" bind:value={editName} required />

      <label for="edit-dob">Date of Birth</label>
      <input id="edit-dob" type="date" bind:value={editDob} />

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (editOpen = false)}><i class="lni lni-xmark"></i>Cancel</button>
        <button type="submit" disabled={editProcessing}><i class="lni lni-check"></i>Save</button>
      </div>
    </form>
  </Modal>

  <Modal title="Add Update for {child.name}" {open} onClose={() => (open = false)}>
    <form on:submit|preventDefault={submit}>
      <label for="text">Update Text</label>
      <textarea id="text" rows="4" bind:value={text} required></textarea>

      <label>Photos</label>
      <FilePicker bind:files />

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (open = false)}><i class="lni lni-xmark"></i>Cancel</button>
        <button type="submit" disabled={processing}><i class="lni lni-check"></i>Add Update</button>
      </div>
    </form>
  </Modal>

  <Modal title="Add Payment for {child.name}" open={payOpen} onClose={() => (payOpen = false)}>
    <form on:submit|preventDefault={submitPay}>
      <label for="pay-month">Month</label>
      <select id="pay-month" bind:value={payMonth} required>
        {#each monthOptions as m}
          <option value={m.value}>{m.label}</option>
        {/each}
      </select>

      <label for="pay-amount">Amount</label>
      <input
        id="pay-amount"
        inputmode="decimal"
        placeholder="0.00"
        value={payAmountDisplay}
        on:input={onAmountInput}
        on:blur={onAmountBlur}
        required
      />

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (payOpen = false)}><i class="lni lni-xmark"></i>Cancel</button>
        <button type="submit" disabled={payProcessing}><i class="lni lni-wallet-1"></i>Add Payment</button>
      </div>
    </form>
  </Modal>

  <Modal title="Send WhatsApp confirmation?" open={!!confirming} onClose={dismissConfirm}>
    {#if confirming}
      <p>
        Payment of <strong>{fmtAmount(confirming.amount)}</strong> for
        <strong>{child.name}</strong> covering
        <strong>{confirming.month}</strong> was logged.
      </p>
      <p>Send a WhatsApp confirmation to all parents of {child.name}?</p>
      <div class="modal-actions">
        <button type="button" class="ghost" on:click={dismissConfirm}><i class="lni lni-xmark"></i>Not now</button>
        <button type="button" on:click={sendConfirmation}><i class="lni lni-telegram"></i>Send confirmation</button>
      </div>
    {/if}
  </Modal>
</Layout>

<style>
  .card-head {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 0.75rem;
  }
  .att-pill {
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
  }
  .att-pill.present { background: #dcfce7; color: #16a34a; }
  .att-pill.absent { background: #fee2e2; color: #dc2626; }
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
  .att-pager {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1rem;
  }
  .parent-picker {
    position: absolute;
    left: 0;
    right: 0;
    top: calc(100% + 0.25rem);
    z-index: 5;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
    max-height: 15rem;
    overflow-y: auto;
  }
  .parent-option {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    padding: 0.5rem 0.6rem;
    background: transparent;
    border: 0;
    border-radius: 0;
    text-align: left;
    color: inherit;
  }
  .parent-option:hover {
    background: var(--border);
  }
  .locked-num {
    background: #f4f5f7;
    color: var(--muted);
  }
</style>
