<script lang="ts">
  import CommandButton from '$lib/CommandButton.svelte';
  import type { Recommendation } from '$lib/types';

  let { recommendation }: { recommendation: Recommendation } = $props();

  let approveLoading = $state(false);
  let rejectLoading = $state(false);

  async function approve() {
    approveLoading = true;
    try {
      const res = await fetch(`/api/recommendations/${recommendation.recommendation_id}/approve`, {
        method: 'POST',
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        if (res.status === 409) {
          window.dispatchEvent(
            new CustomEvent('farm:toast', {
              detail: { message: 'Another zone is already irrigating.' },
            })
          );
        } else {
          window.dispatchEvent(
            new CustomEvent('farm:toast', {
              detail: { message: data.detail || 'Command failed \u2014 tap to retry' },
            })
          );
        }
      }
      // On success: card removed by WebSocket recommendation_queue delta
    } catch {
      window.dispatchEvent(
        new CustomEvent('farm:toast', {
          detail: { message: 'Command failed \u2014 tap to retry' },
        })
      );
    } finally {
      approveLoading = false;
    }
  }

  async function reject() {
    rejectLoading = true;
    try {
      const res = await fetch(`/api/recommendations/${recommendation.recommendation_id}/reject`, {
        method: 'POST',
      });
      if (!res.ok) {
        window.dispatchEvent(
          new CustomEvent('farm:toast', {
            detail: { message: 'Command failed \u2014 tap to retry' },
          })
        );
      }
    } catch {
      window.dispatchEvent(
        new CustomEvent('farm:toast', {
          detail: { message: 'Command failed \u2014 tap to retry' },
        })
      );
    } finally {
      rejectLoading = false;
    }
  }
</script>

<div class="rec-card">
  <p class="action-description">{recommendation.action_description}</p>
  <p class="sensor-reading">{recommendation.sensor_reading}</p>
  <p class="explanation">{recommendation.explanation}</p>
  <div class="controls">
    <CommandButton
      label="Approve"
      variant="approve"
      loading={approveLoading}
      disabled={rejectLoading}
      aria-label="Approve: {recommendation.action_description}"
      onclick={approve}
    />
    <CommandButton
      label="Reject"
      variant="reject"
      loading={rejectLoading}
      disabled={approveLoading}
      aria-label="Reject: {recommendation.action_description}"
      onclick={reject}
    />
  </div>
</div>

<style>
  .rec-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-left: 3px solid var(--color-accent);
    border-radius: var(--radius-md);
    padding: var(--spacing-md);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
    box-shadow: var(--shadow-card);
  }

  .action-description {
    font-size: 16px;
    font-weight: 600;
    line-height: 1.5;
    color: var(--color-text-primary);
  }

  .sensor-reading {
    font-size: 14px;
    font-weight: 400;
    line-height: 1.4;
    color: var(--color-text-secondary);
  }

  .explanation {
    font-size: 14px;
    font-weight: 400;
    line-height: 1.4;
    color: var(--color-text-secondary);
    font-style: italic;
  }

  .controls {
    display: flex;
    justify-content: space-between;
    gap: var(--spacing-sm);
    margin-top: var(--spacing-sm);
  }

  .controls :global(.cmd-btn) {
    flex: 1;
  }
</style>
