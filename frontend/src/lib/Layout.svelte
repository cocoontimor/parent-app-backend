<script>
  import { inertia, page, router } from '@inertiajs/svelte'

  const staffGroups = [
    { label: null, items: [
      { href: '/', label: 'Dashboard', icon: 'lni-dashboard-square-1' },
    ] },
    { label: 'People', items: [
      { href: '/children/', label: 'Children', icon: 'lni-user-multiple-4' },
      { href: '/classes/', label: 'Classes', icon: 'lni-school-bench-1' },
      { href: '/users/', label: 'Users', icon: 'lni-user-4' },
    ] },
    { label: 'Communication', items: [
      { href: '/announcements/', label: 'Announcements', icon: 'lni-megaphone-1' },
      { href: '/urgent-alerts/', label: 'Urgent Alerts', icon: 'lni-bell-1' },
      { href: '/messages/', label: 'Messages', icon: 'lni-message-3-text' },
    ] },
    { label: 'Learning', items: [
      { href: '/elearning/courses/', label: 'Courses', icon: 'lni-book-1' },
      { href: '/elearning/cohorts/', label: 'Cohorts', icon: 'lni-graduation-cap-1' },
    ] },
    { label: 'Finance', items: [
      { href: '/payments/', label: 'Payments', icon: 'lni-wallet-1' },
    ] },
  ]

  // Teachers get the People + Finance surfaces, scoped to their classes.
  const teacherGroups = [
    { label: null, items: [
      { href: '/', label: 'Dashboard', icon: 'lni-dashboard-square-1' },
    ] },
    { label: 'People', items: [
      { href: '/children/', label: 'Children', icon: 'lni-user-multiple-4' },
      { href: '/classes/', label: 'Classes', icon: 'lni-school-bench-1' },
      { href: '/users/', label: 'Parents', icon: 'lni-user-4' },
    ] },
    { label: 'Communication', items: [
      { href: '/announcements/', label: 'Announcements', icon: 'lni-megaphone-1' },
    ] },
    { label: 'Finance', items: [
      { href: '/payments/', label: 'Payments', icon: 'lni-wallet-1' },
    ] },
  ]

  // Parents get a trimmed, view-only sidebar.
  const parentGroups = [
    { label: null, items: [
      { href: '/', label: 'Home', icon: 'lni-home-2' },
      { href: '/children/', label: 'My Children', icon: 'lni-user-multiple-4' },
      { href: '/announcements/', label: 'Announcements', icon: 'lni-megaphone-1' },
      { href: '/payments/', label: 'Payments', icon: 'lni-wallet-1' },
    ] },
  ]

  $: isStaff = $page.props.auth?.user?.is_staff_group
  $: isTeacher = $page.props.auth?.user?.is_teacher
  $: groups = isStaff ? staffGroups : isTeacher ? teacherGroups : parentGroups

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
      {#each groups as group}
        <div class="nav-group">
          {#if group.label}
            <div class="nav-group-label">{group.label}</div>
          {/if}
          {#each group.items as item}
            <a href={item.href} use:inertia class:active={isActive(item.href)}>
              <i class="lni {item.icon}"></i>{item.label}
            </a>
          {/each}
        </div>
      {/each}
    </nav>
  </aside>

  <div class="main">
    <header class="topbar">
      <button class="ghost" on:click={logout}><i class="lni lni-exit"></i>Logout</button>
    </header>
    <main class="content">
      <slot />
    </main>
  </div>
</div>
