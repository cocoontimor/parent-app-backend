<script>
  import { inertia, page, router } from '@inertiajs/svelte'

  const staffItems = [
    { href: '/', label: 'Dashboard' },
    { href: '/children/', label: 'Children' },
    { href: '/classes/', label: 'Classes' },
    { href: '/users/', label: 'Users' },
    { href: '/announcements/', label: 'Announcements' },
    { href: '/elearning/', label: 'E-Learning' },
    { href: '/urgent-alerts/', label: 'Urgent Alerts' },
    { href: '/payments/', label: 'Payments' },
    { href: '/messages/', label: 'Messages' },
  ]

  // Parents get a trimmed, view-only sidebar.
  const parentItems = [
    { href: '/', label: 'Home' },
    { href: '/children/', label: 'My Children' },
    { href: '/announcements/', label: 'Announcements' },
    { href: '/payments/', label: 'Payments' },
  ]

  $: isStaff = $page.props.auth?.user?.is_staff_group
  $: items = isStaff ? staffItems : parentItems

  $: current = $page.url

  function isActive(href) {
    if (href === '/') return current === '/'
    return current.startsWith(href)
  }

  function logout() {
    router.post('/logout/')
  }
</script>

<div class="shell">
  <aside class="sidebar">
    <div class="brand">Cocoon</div>
    <nav class="nav">
      {#each items as item}
        <a href={item.href} use:inertia class:active={isActive(item.href)}>{item.label}</a>
      {/each}
    </nav>
  </aside>

  <div class="main">
    <header class="topbar">
      <button class="ghost" on:click={logout}>Logout</button>
    </header>
    <main class="content">
      <slot />
    </main>
  </div>
</div>
