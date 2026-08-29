<script>
  import { useForm } from '@inertiajs/svelte'

  export let errors = {}

  const form = useForm({ username: '', password: '' })

  function submit() {
    $form.post('/login/submit/')
  }
</script>

<div class="container" style="max-width: 380px; margin: 12vh auto 0;">
  <div class="card">
    <h1 style="margin-bottom: 0.25rem;">Cocoon Admin</h1>
    <p style="color: var(--muted); margin-top: 0;">Staff sign in</p>

    {#if errors.username}
      <div class="error">{errors.username}</div>
    {/if}

    <form on:submit|preventDefault={submit}>
      <label for="username">Username</label>
      <input id="username" type="text" bind:value={$form.username} autocomplete="username" required />

      <label for="password">Password</label>
      <input id="password" type="password" bind:value={$form.password} autocomplete="current-password" required />

      <button type="submit" disabled={$form.processing} style="width: 100%;">Log in</button>
    </form>
  </div>
</div>
