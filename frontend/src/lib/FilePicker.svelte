<script>
  // Accumulating file picker: click or drag-and-drop, previews, per-file remove.
  // `files` is bindable and holds the raw File[] the parent submits.
  import { onDestroy } from 'svelte'

  export let files = []
  export let accept = 'image/*'
  export let multiple = true

  let input
  let entries = [] // [{ file, url }] — url is an object URL for image previews
  let dragging = false

  function sync() {
    entries = entries
    files = entries.map((e) => e.file)
  }

  function addFiles(list) {
    for (const file of list) {
      // Skip exact duplicates so re-picking the same file doesn't stack it.
      if (entries.some((e) => e.file.name === file.name && e.file.size === file.size)) continue
      const url = file.type.startsWith('image/') ? URL.createObjectURL(file) : ''
      entries.push({ file, url })
      if (!multiple) break
    }
    sync()
  }

  function remove(i) {
    const [gone] = entries.splice(i, 1)
    if (gone?.url) URL.revokeObjectURL(gone.url)
    sync()
  }

  function onChange(e) {
    addFiles(e.target.files)
    input.value = '' // let the same file be picked again / more added later
  }

  function onDrop(e) {
    e.preventDefault()
    dragging = false
    if (e.dataTransfer?.files?.length) addFiles(e.dataTransfer.files)
  }

  // When the parent clears `files` (e.g. after submit), drop our previews too.
  $: if (files.length === 0 && entries.length) {
    entries.forEach((e) => e.url && URL.revokeObjectURL(e.url))
    entries = []
  }

  onDestroy(() => entries.forEach((e) => e.url && URL.revokeObjectURL(e.url)))
</script>

<div
  class="filepicker"
  class:dragging
  role="button"
  tabindex="0"
  on:click={() => input.click()}
  on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), input.click())}
  on:dragover|preventDefault={() => (dragging = true)}
  on:dragleave={() => (dragging = false)}
  on:drop={onDrop}
>
  <i class="lni lni-cloud-upload"></i>
  <span>Drag {multiple ? 'files' : 'a file'} here or <u>browse</u></span>
</div>
<input bind:this={input} type="file" {accept} {multiple} on:change={onChange} style="display: none;" />

{#if entries.length}
  <div class="filepicker-list">
    {#each entries as e, i (e.file.name + e.file.size)}
      <div class="filepicker-item">
        {#if e.url}
          <img src={e.url} alt={e.file.name} />
        {:else}
          <span class="filepicker-file"><i class="lni lni-gallery"></i></span>
        {/if}
        <span class="filepicker-name">{e.file.name}</span>
        <button type="button" aria-label="Remove" on:click={() => remove(i)}><i class="lni lni-xmark"></i></button>
      </div>
    {/each}
  </div>
{/if}
