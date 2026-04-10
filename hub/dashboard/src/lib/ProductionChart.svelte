<script lang="ts">
  import uPlot from 'uplot';
  import 'uplot/dist/uPlot.min.css';
  import { onMount, onDestroy } from 'svelte';

  let container: HTMLDivElement;
  let chart: uPlot | null = null;
  let loading = $state(true);
  let insufficientData = $state(false);

  function buildOpts(width: number, height: number): uPlot.Options {
    return {
      width,
      height,
      series: [
        {},
        {
          label: 'Actual',
          stroke: '#4ade80',
          width: 1.5,
        },
        {
          label: 'Expected',
          stroke: '#94a3b8',
          width: 1.5,
          dash: [4, 4],
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

  function getChartHeight(): number {
    if (typeof window !== 'undefined' && window.innerWidth >= 640) return 200;
    return 160;
  }

  async function loadAndRender() {
    loading = true;
    insufficientData = false;
    if (chart) {
      chart.destroy();
      chart = null;
    }

    let dates: string[] = [];
    let actual: number[] = [];
    let expected: number[] = [];

    try {
      const res = await fetch('/api/flock/egg-history?days=30');
      if (res.ok) {
        const data = await res.json();
        dates = data.dates ?? [];
        actual = data.actual ?? [];
        expected = data.expected ?? [];
      }
    } catch {
      // Network error — treat as empty
    }

    if (dates.length < 3) {
      loading = false;
      insufficientData = true;
      return;
    }

    const timestamps = dates.map((d: string) => new Date(d).getTime() / 1000);

    loading = false;

    requestAnimationFrame(() => {
      if (!container) return;
      const width = container.clientWidth || 300;
      const height = getChartHeight();
      const opts = buildOpts(width, height);
      chart = new uPlot(opts, [timestamps, actual, expected] as uPlot.AlignedData, container);
    });
  }

  let resizeObserver: ResizeObserver | null = null;

  onMount(() => {
    loadAndRender();

    resizeObserver = new ResizeObserver(() => {
      if (chart && container) {
        chart.setSize({ width: container.clientWidth, height: getChartHeight() });
      }
    });
    resizeObserver.observe(container);
  });

  onDestroy(() => {
    chart?.destroy();
    resizeObserver?.disconnect();
  });
</script>

<div
  class="production-chart-wrap"
  bind:this={container}
  aria-label="Egg production chart — actual vs expected, last 30 days"
>
  {#if loading}
    <div class="skeleton" aria-busy="true"></div>
  {:else if insufficientData}
    <div class="insufficient-state">
      <div class="skeleton skeleton-bg"></div>
      <p class="insufficient-msg">Not enough data yet — check back in a few days</p>
    </div>
  {/if}
</div>

<style>
  .production-chart-wrap {
    width: 100%;
    min-height: 160px;
    position: relative;
    background: var(--color-bg);
  }

  @media (min-width: 640px) {
    .production-chart-wrap {
      min-height: 200px;
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

  .insufficient-state {
    position: relative;
    width: 100%;
  }

  .skeleton-bg {
    opacity: 1;
  }

  .insufficient-msg {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 14px;
    font-weight: 400;
    color: var(--color-muted);
    text-align: center;
    width: 80%;
    line-height: 1.4;
  }
</style>
