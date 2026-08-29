<script>
  import { router } from '@inertiajs/svelte'
  import Layout from '../lib/Layout.svelte'

  export let children = []
  export let circles = []
  export let announcements = []

  $: pendingAcks = announcements.filter((a) => a.ack_count === 0).length
  $: recent = announcements.slice(0, 5)

  const stats = () => [
    { label: 'Children', value: children.length },
    { label: 'Classes', value: circles.length },
    { label: 'Pending Acks', value: pendingAcks },
    { label: 'Announcements', value: announcements.length },
  ]
</script>

<Layout>
  <div class="page-head"><h1>Dashboard</h1></div>

  <div class="stat-grid">
    {#each stats() as s}
      <div class="card stat">
        <div class="label">{s.label}</div>
        <div class="value">{s.value}</div>
      </div>
    {/each}
  </div>

  <div class="card">
    <h3 style="margin-bottom: 1rem;">Recent Announcements</h3>
    {#if recent.length === 0}
      <p style="color: var(--muted); margin: 0;">No announcements yet.</p>
    {:else}
      {#each recent as a}
        <div
          class="clickable"
          style="padding: 0.6rem 0; border-bottom: 1px solid var(--border); cursor: pointer;"
          on:click={() => router.visit(`/announcements/${a.id}/`)}
        >
          <strong>{a.title}</strong>
          <span style="color: var(--muted);"> · {a.ack_count} acks</span>
        </div>
      {/each}
    {/if}
  </div>
</Layout>
