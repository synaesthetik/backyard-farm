import { describe, it, expect, afterEach, vi, beforeEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/svelte';
import RecommendationCard from './RecommendationCard.svelte';
import type { Recommendation } from './types';

afterEach(() => cleanup());

function makeRec(overrides: Partial<Recommendation> = {}): Recommendation {
  return {
    recommendation_id: 'rec-001',
    zone_id: 'raised-bed-1',
    rec_type: 'irrigate',
    action_description: 'Irrigate raised-bed-1',
    sensor_reading: 'Moisture: 18% VWC (target range: 40–60%)',
    explanation: 'Below low threshold for 2h',
    ...overrides,
  };
}

describe('RecommendationCard', () => {
  it('renders action_description', () => {
    render(RecommendationCard, { recommendation: makeRec() });
    expect(screen.getByText('Irrigate raised-bed-1')).toBeTruthy();
  });

  it('renders sensor_reading', () => {
    render(RecommendationCard, { recommendation: makeRec() });
    expect(screen.getByText('Moisture: 18% VWC (target range: 40–60%)')).toBeTruthy();
  });

  it('renders explanation', () => {
    render(RecommendationCard, { recommendation: makeRec() });
    expect(screen.getByText('Below low threshold for 2h')).toBeTruthy();
  });

  it('has Approve button', () => {
    render(RecommendationCard, { recommendation: makeRec() });
    expect(screen.getByText('Approve')).toBeTruthy();
  });

  it('has Reject button', () => {
    render(RecommendationCard, { recommendation: makeRec() });
    expect(screen.getByText('Reject')).toBeTruthy();
  });

  it('calls fetch with approve URL when Approve is clicked', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal('fetch', mockFetch);

    render(RecommendationCard, { recommendation: makeRec({ recommendation_id: 'rec-001' }) });
    const approveBtn = screen.getByText('Approve');
    await fireEvent.click(approveBtn);

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/recommendations/rec-001/approve',
      expect.objectContaining({ method: 'POST' })
    );

    vi.unstubAllGlobals();
  });

  it('calls fetch with reject URL when Reject is clicked', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal('fetch', mockFetch);

    render(RecommendationCard, { recommendation: makeRec({ recommendation_id: 'rec-002' }) });
    const rejectBtn = screen.getByText('Reject');
    await fireEvent.click(rejectBtn);

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/recommendations/rec-002/reject',
      expect.objectContaining({ method: 'POST' })
    );

    vi.unstubAllGlobals();
  });
});
