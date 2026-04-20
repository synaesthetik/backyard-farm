<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';

  onMount(() => {
    const saved = localStorage.getItem('tutorial_step');
    const step = saved ? parseInt(saved, 10) : 1;
    goto(`/tutorial/${Math.min(step, 8)}`, { replaceState: true });
  });
</script>
