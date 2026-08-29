<script>
  import { useForm, router, page } from '@inertiajs/svelte'
  import Layout from '../../lib/Layout.svelte'
  import Modal from '../../lib/Modal.svelte'

  export let payments = []
  export let children = []
  export let created = null

  $: isStaff = $page.props.auth?.user?.is_staff_group

  let open = false
  const form = useForm({ child: '', month: '', amount: '' })

  // The create flow redirects back with `created` set; open the confirmation
  // modal for that payment so staff can send the WhatsApp receipt to parents.
  let confirming = created

  function submit() {
    $form.post('/payments/create/', {
      onSuccess: () => {
        open = false
        $form.reset()
      },
    })
  }

  function sendConfirmation() {
    router.post(`/payments/${confirming.id}/send-confirmation/`, {}, {
      onFinish: () => (confirming = null),
    })
  }

  function dismiss() {
    confirming = null
    router.visit('/payments/', { replace: true, preserveScroll: true })
  }

  const fmtDate = (v) => new Date(v).toLocaleDateString()
</script>

<Layout>
  <div class="page-head">
    <h1>Payments</h1>
    {#if isStaff}
      <button on:click={() => (open = true)}>Log Payment</button>
    {/if}
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Child</th><th>Month</th><th>Amount</th><th>Logged</th></tr>
      </thead>
      <tbody>
        {#each payments as p}
          <tr>
            <td>{p.child_name}</td>
            <td>{p.month}</td>
            <td>{p.amount}</td>
            <td>{fmtDate(p.created)}</td>
          </tr>
        {:else}
          <tr><td colspan="4" class="empty">No payments logged yet.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>

  <Modal title="Log Payment" {open} onClose={() => (open = false)}>
    <form on:submit|preventDefault={submit}>
      <label for="child">Child</label>
      <select id="child" bind:value={$form.child} required>
        <option value="" disabled>Select a child</option>
        {#each children as c}
          <option value={c.id}>{c.name}</option>
        {/each}
      </select>

      <label for="month">Month</label>
      <input id="month" placeholder="2026-08" bind:value={$form.month} required />

      <label for="amount">Amount</label>
      <input id="amount" type="number" step="0.01" min="0" bind:value={$form.amount} required />

      <div class="modal-actions">
        <button type="button" class="ghost" on:click={() => (open = false)}>Cancel</button>
        <button type="submit" disabled={$form.processing}>Log Payment</button>
      </div>
    </form>
  </Modal>

  <Modal title="Send WhatsApp confirmation?" open={!!confirming} onClose={dismiss}>
    {#if confirming}
      <p>
        Payment of <strong>{confirming.amount}</strong> for
        <strong>{confirming.child_name}</strong> covering
        <strong>{confirming.month}</strong> was logged.
      </p>
      <p>Send a WhatsApp confirmation to all parents of {confirming.child_name}?</p>
      <div class="modal-actions">
        <button type="button" class="ghost" on:click={dismiss}>Not now</button>
        <button type="button" on:click={sendConfirmation}>Send confirmation</button>
      </div>
    {/if}
  </Modal>
</Layout>
