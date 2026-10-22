<script>
  // In-app confirmation dialog, replacing window.confirm.
  import Modal from './Modal.svelte'

  export let open = false
  export let title = 'Confirm'
  export let message = ''
  export let confirmLabel = 'Confirm'
  export let danger = false // red confirm button for destructive actions
  export let onConfirm = () => {}
  export let onClose = () => {}
</script>

<Modal {title} {open} {onClose}>
  <p style="margin: 0 0 1.25rem;">{message}</p>
  <div class="modal-actions">
    <button type="button" class="ghost" on:click={onClose}><i class="lni lni-xmark"></i>Cancel</button>
    <button type="button" class={danger ? 'danger' : ''} on:click={onConfirm}>
      <i class="lni lni-check"></i>{confirmLabel}
    </button>
  </div>
</Modal>
