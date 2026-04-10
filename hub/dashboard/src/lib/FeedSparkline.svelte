<script lang="ts">
  let { values = [] }: { values: number[] } = $props();

  function toPolylinePoints(vals: number[], width = 80, height = 24): string {
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const range = max - min || 1; // division-by-zero guard
    return vals
      .map((v, i) => {
        const x = (i / (vals.length - 1)) * width;
        const y = height - ((v - min) / range) * height;
        return `${x},${y}`;
      })
      .join(' ');
  }
</script>

{#if values.length >= 2}
  <svg
    width="80"
    height="24"
    viewBox="0 0 80 24"
    aria-hidden="true"
    style="display: block; flex-shrink: 0;"
  >
    <polyline
      points={toPolylinePoints(values)}
      fill="none"
      stroke="var(--color-accent)"
      stroke-width="1.5"
    />
  </svg>
{/if}
