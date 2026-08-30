<script>
  import { inertia } from '@inertiajs/svelte'
  import Layout from '../../lib/Layout.svelte'

  export let announcement
  export let acks = []

  const fmtDateTime = (v) => new Date(v).toLocaleString()
</script>

<Layout>
  <div class="page-head">
    <h1>{announcement.title}</h1>
    <a href="/announcements/" use:inertia><button class="ghost">← Back</button></a>
  </div>

  <div class="card" style="margin-bottom: 1rem;">
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
      <div><span style="color: var(--muted);">Created By:</span> {announcement.created_by_name}</div>
      <div><span style="color: var(--muted);">Ack Count:</span> {announcement.ack_count}</div>
      <div><span style="color: var(--muted);">Created:</span> {fmtDateTime(announcement.created)}</div>
    </div>
    <p style="margin-top: 1rem; white-space: pre-wrap;">{announcement.body}</p>

    {#if announcement.photos?.length}
      <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 1rem;">
        {#each announcement.photos as p}
          <a href={p.image} target="_blank" rel="noopener">
            <img src={p.image} alt="" style="height: 120px; border-radius: 6px; object-fit: cover;" />
          </a>
        {/each}
      </div>
    {/if}
  </div>

  <div class="card">
    <h3 style="margin-bottom: 1rem;">Acknowledgements</h3>
    <div class="table-wrap" style="border: 0;">
      <table>
        <thead>
          <tr><th>Parent</th><th>Acknowledged At</th></tr>
        </thead>
        <tbody>
          {#each acks as a}
            <tr><td>{a.parent_name}</td><td>{fmtDateTime(a.created)}</td></tr>
          {:else}
            <tr><td colspan="2" class="empty">No acknowledgements yet.</td></tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>
</Layout>
