<script lang="ts">
  import uPlot from 'uplot';
  import 'uplot/dist/uPlot.min.css';
  import { onMount, onDestroy } from 'svelte';

  let {
    zoneId,
    sensorType,
    days = $bindable(7),
  }: {
    zoneId: string;
    sensorType: string;
    days?: number;
  } = $props();

  let container: HTMLDivElement;
  let chart: uPlot | null = null;
  let loading = $state(true);
  let empty = $state(false);

  const seriesColors: Record<string, string> = {
    moisture: '#4ade80',
    ph: '#60a5fa',
    temperature: '#fb923c',
  };

  const seriesLabels: Record<string, string> = {
    moisture: 'VWC %',
    ph: 'pH',
    temperature: '°C',
  };

  function buildOpts(width: number): uPlot.Options {
    const color = seriesColors[sensorType] ?? '#94a3b8';
    const label = seriesLabels[sensorType] ?? sensorType;
    return {
      width,
      height: 160,
      series: [
        {},
        {
          label,
          stroke: color,
          width: 1.5,
        },
      ],
      axes: [
        {
          stroke: '#94a3b8',
          grid: { stroke: '#2d3149' },
          ticks: { stroke: '#2d3149' },
          size: 14,
        },
        {
          stroke: '#94a3b8',
          grid: { stroke: '#2d3149' },
          ticks: { stroke: '#2d3149' },
          size: 14,
        },
      ],
      cursor: {
        stroke: '#6b7280',
      },
    };
  }

  async function loadAndRender() {
    loading = true;
    empty = false;
    if (chart) {
      chart.destroy();
      chart = null;
    }

    let data: { ts: string; value: number | null }[] = [];
    try {
      const res = await fetch(`/api/zones/${zoneId}/history?sensor_type=${sensorType}&days=${days}`);
      if (res.ok) {
        data = await res.json();
      }
    } catch {
      // Network error — treat as empty
    }

    const timestamps = data.map((d) => new Date(d.ts).getTime() / 1000);
    const values = data.map((d) => d.value);

    if (timestamps.length === 0) {
      loading = false;
      empty = true;
      return;
    }

    loading = false;

    requestAnimationFrame(() => {
      if (!container) return;
      const width = container.clientWidth || 300;
      const opts = buildOpts(width);
      chart = new uPlot(opts, [timestamps, values] as uPlot.AlignedData, container);
    });
  }

  let resizeObserver: ResizeObserver | null = null;

  onMount(() => {
    loadAndRender();

    resizeObserver = new ResizeObserver(() => {
      if (chart && container) {
        chart.setSize({ width: container.clientWidth, height: chart.height });
      }
    });
    resizeObserver.observe(container);
  });

  onDestroy(() => {
    chart?.destroy();
    resizeObserver?.disconnect();
  });

  $effect(() => {
    if (days) loadAndRender();
  });
</script>

<div class="sensor-chart-wrap" bind:this={container}>
  {#if loading}
    <div class="skeleton" aria-busy="true"></div>
  {:else if empty}
    <div class="empty-state">No data for this period</div>
  {/if}
</div>

<style>
  .sensor-chart-wrap {
    width: 100%;
    min-height: 160px;
    position: relative;
  }

  @media (min-width: 640px) {
    .sensor-chart-wrap {
      min-height: 200px;
    }

    .sensor-chart-wrap :global(.u-wrap) {
      height: 200px !important;
    }
  }

  .skeleton {
    width: 100%;
    height: 160px;
    background: var(--color-surface);
    border-radius: 4px;
  }

  @media (min-width: 640px) {
    .skeleton {
      height: 200px;
    }
  }

  .empty-state {
    width: 100%;
    height: 160px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--color-surface);
    color: var(--color-muted);
    font-size: 14px;
    font-weight: 400;
    border-radius: 4px;
  }

  @media (min-width: 640px) {
    .empty-state {
      height: 200px;
    }
  }
</style>
