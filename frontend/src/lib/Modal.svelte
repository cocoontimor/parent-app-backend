<script>
  export let title = ''
  export let open = false
  export let onClose = () => {}
</script>

{#if open}
  <div class="modal-backdrop" on:click={onClose}>
    <div class="modal" on:click|stopPropagation>
      <h3>{title}</h3>
      <slot />
    </div>
  </div>
{/if}
