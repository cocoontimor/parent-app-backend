<script>
  import Layout from '../lib/Layout.svelte'

  export let users = []
</script>

<Layout>
  <div class="page-head"><h1>Users</h1></div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Username</th><th>Name</th><th>Email</th></tr>
      </thead>
      <tbody>
        {#each users as u}
          <tr>
            <td>{u.username}</td>
            <td>{u.display_name || '-'}</td>
            <td>{u.email || '-'}</td>
          </tr>
        {:else}
          <tr><td colspan="3" class="empty">No users yet.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>
</Layout>
