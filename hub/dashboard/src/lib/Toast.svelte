<script lang="ts">
  import { XCircle } from 'lucide-svelte';

  let { message = '', visible = $bindable(false) }: { message: string; visible: boolean } = $props();

  let timer: ReturnType<typeof setTimeout> | null = null;

  $effect(() => {
    if (visible) {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => { visible = false; }, 5000);
    }
  });
</script>

{#if visible}
<div class="toast" role="alert" aria-live="assertive">
  <XCircle size={16} />
  <span>{message}</span>
</div>
{/if}

<style>
  .toast {
    position: fixed;
    bottom: calc(56px + env(safe-area-inset-bottom, 0px) + 8px);
    left: 50%;
    transform: translateX(-50%);
    width: min(calc(100% - 32px), 400px);
    background: var(--color-offline);
    color: var(--color-text-primary);
    border-radius: 8px;
    padding: var(--spacing-sm);
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: 16px;
    font-weight: 400;
    line-height: 1.5;
    z-index: 30;
  }
</style>
