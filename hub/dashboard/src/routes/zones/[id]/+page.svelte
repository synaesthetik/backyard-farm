<script>
  import { page } from '$app/stores';
  import { dashboardStore } from '$lib/ws.svelte';

  const zoneId = $derived($page.params.id);
</script>

<h2 class="page-heading">{zoneId}</h2>
<p class="placeholder">Zone detail will be implemented in plan 02-05.</p>

<style>
  .page-heading {
    font-size: 20px;
    font-weight: 600;
    line-height: 1.2;
    margin-bottom: var(--spacing-lg);
  }
  .placeholder {
    color: var(--color-muted);
    font-size: 16px;
  }
</style>
