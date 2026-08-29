<script>
  import Layout from '../lib/Layout.svelte'

  export let messages = []

  const statusColors = {
    pending: 'gray',
    sent: 'blue',
    delivered: 'green',
    failed: 'red',
  }
  const fmtDateTime = (v) => (v ? new Date(v).toLocaleString() : '-')
</script>

<Layout>
  <div class="page-head"><h1>Messages</h1></div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Recipient</th><th>Template</th><th>Body</th><th>Status</th><th>Sent At</th></tr>
      </thead>
      <tbody>
        {#each messages as m}
          <tr>
            <td>{m.recipient}</td>
            <td>{m.template || '-'}</td>
            <td class="ellipsis">{m.body}</td>
            <td><span class="tag {statusColors[m.status] || 'gray'}">{m.status}</span></td>
            <td>{fmtDateTime(m.sent_at)}</td>
          </tr>
        {:else}
          <tr><td colspan="5" class="empty">No messages yet.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>
</Layout>
