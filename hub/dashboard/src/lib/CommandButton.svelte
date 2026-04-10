<script lang="ts">
  import { Loader2 } from 'lucide-svelte';

  let {
    label = '',
    variant = 'default',
    loading = false,
    disabled = false,
    onclick = () => {},
  }: {
    label: string;
    variant?: 'default' | 'approve' | 'reject';
    loading?: boolean;
    disabled?: boolean;
    onclick?: () => void;
  } = $props();
</script>

<button
  class="cmd-btn"
  class:approve={variant === 'approve'}
  class:reject={variant === 'reject'}
  class:loading
  disabled={loading || disabled}
  aria-disabled={loading || disabled}
  aria-busy={loading}
  onclick={onclick}
>
  {#if loading}
    <span class="spinner"><Loader2 size={16} /></span>
  {:else}
    {label}
  {/if}
</button>

<style>
  .cmd-btn {
    min-height: 44px;
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    color: var(--color-text-primary);
    font-family: inherit;
    font-size: 16px;
    font-weight: 600;
    line-height: 1.5;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-sm);
    transition: opacity var(--transition-fast), background-color var(--transition-fast), transform var(--transition-fast), box-shadow var(--transition-fast);
  }
  .cmd-btn:hover:not(:disabled) {
    background: var(--color-surface-hover);
  }
  .cmd-btn:active:not(:disabled) {
    transform: scale(0.97);
  }
  .cmd-btn:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }
  .cmd-btn.approve {
    background: var(--color-accent);
    color: var(--color-bg);
    border-color: var(--color-accent);
    box-shadow: 0 0 0 0 rgba(74, 222, 128, 0);
  }
  .cmd-btn.approve:hover:not(:disabled) {
    background: #5ce98e;
    box-shadow: 0 0 12px rgba(74, 222, 128, 0.25);
  }
  .cmd-btn.reject {
    background: var(--color-surface);
    border-color: var(--color-border);
    color: var(--color-text-primary);
  }
  .cmd-btn.reject:hover:not(:disabled) {
    border-color: var(--color-offline);
    color: var(--color-offline);
  }
  .spinner {
    display: inline-flex;
    animation: spin 1s linear infinite;
    color: var(--color-accent);
  }
  .cmd-btn.approve .spinner {
    color: var(--color-bg);
  }
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
</style>
