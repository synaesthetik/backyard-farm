<script lang="ts">
  import { Egg } from 'lucide-svelte';
</script>

<div class="hen-indicator" aria-live="polite">
  <span class="hen-icon" aria-hidden="true">
    <Egg size={16} />
  </span>
  <span class="hen-label">Hen present</span>
</div>

<style>
  .hen-indicator {
    display: inline-flex;
    flex-direction: row;
    align-items: center;
    gap: var(--spacing-xs);
  }

  .hen-icon {
    display: inline-flex;
    align-items: center;
    color: var(--color-accent);
    animation: hen-pulse 2s ease-in-out infinite;
  }

  .hen-label {
    font-size: 16px;
    font-weight: 600;
    line-height: 1.5;
    color: var(--color-accent);
  }

  @keyframes hen-pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50%       { transform: scale(1.15); opacity: 0.7; }
  }
</style>
