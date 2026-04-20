import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import { render, cleanup } from '@testing-library/svelte';

// Static imports — avoids cold-compile timeout on first dynamic import
import Step3 from './3/+page.svelte';
import Step4 from './4/+page.svelte';
import Step5 from './5/+page.svelte';
import Step8 from './8/+page.svelte';

// goto mock from vitest alias defined in vitest.config.ts
import { goto } from '$app/navigation';

beforeEach(() => {
  // jsdom provides localStorage but clear() may not be available on some setups;
  // use vi.stubGlobal for a clean in-memory store each test
  const store: Record<string, string> = {};
  vi.stubGlobal('localStorage', {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => { store[k] = String(v); },
    removeItem: (k: string) => { delete store[k]; },
    clear: () => { Object.keys(store).forEach(k => delete store[k]); },
    get length() { return Object.keys(store).length; },
    key: (i: number) => Object.keys(store)[i] ?? null,
  });
  vi.clearAllMocks();
});
afterEach(() => {
  vi.unstubAllGlobals();
  cleanup();
});

// ---- Step 3: "I did this" advances localStorage ----

describe('Tutorial step 3 — advance on markDone', () => {
  it('writes tutorial_step=4 to localStorage when "I did this" is clicked', () => {
    const { container } = render(Step3);
    const btn = container.querySelector('button.btn-primary') as HTMLButtonElement;
    expect(btn).toBeTruthy();
    btn.click();
    expect(localStorage.getItem('tutorial_step')).toBe('4');
  });

  it('calls goto(/tutorial/4) when "I did this" is clicked', () => {
    const { container } = render(Step3);
    const btn = container.querySelector('button.btn-primary') as HTMLButtonElement;
    expect(btn).toBeTruthy();
    btn.click();
    expect(goto).toHaveBeenCalledWith('/tutorial/4');
  });
});

// ---- Step 8: final step marks tutorial_completed ----

describe('Tutorial step 8 — completion', () => {
  it('sets tutorial_completed=true in localStorage when "Finish" is clicked', () => {
    const { container } = render(Step8);
    const btn = container.querySelector('button.btn-primary') as HTMLButtonElement;
    expect(btn).toBeTruthy();
    btn.click();
    expect(localStorage.getItem('tutorial_completed')).toBe('true');
  });

  it('removes tutorial_step from localStorage when "Finish" is clicked', () => {
    localStorage.setItem('tutorial_step', '8');
    const { container } = render(Step8);
    const btn = container.querySelector('button.btn-primary') as HTMLButtonElement;
    expect(btn).toBeTruthy();
    btn.click();
    expect(localStorage.getItem('tutorial_step')).toBeNull();
  });

  it('does NOT call goto(/tutorial/9) on step 8 finish', () => {
    const { container } = render(Step8);
    const btn = container.querySelector('button.btn-primary') as HTMLButtonElement;
    expect(btn).toBeTruthy();
    btn.click();
    // goto may be called to stay on step 8 but must NOT call /tutorial/9
    const calls = (goto as ReturnType<typeof vi.fn>).mock.calls;
    const wentToStep9 = calls.some(([arg]: [string]) => arg === '/tutorial/9');
    expect(wentToStep9).toBe(false);
  });
});

// ---- Step 4: "Back" link navigates to /tutorial/3 ----

describe('Tutorial step 4 — back navigation', () => {
  it('renders a back link to /tutorial/3', () => {
    const { container } = render(Step4);
    const backLink = container.querySelector('a.btn-secondary') as HTMLAnchorElement;
    expect(backLink).toBeTruthy();
    expect(backLink.getAttribute('href')).toBe('/tutorial/3');
  });
});

// ---- No redirect guard on mid-tour load ----

describe('Tutorial step 5 — no auto-redirect', () => {
  it('renders step 5 page regardless of localStorage tutorial_step value', () => {
    localStorage.setItem('tutorial_step', '5');
    const { container } = render(Step5);
    // Page should render its content (not redirect away)
    const btn = container.querySelector('button.btn-primary');
    expect(btn).toBeTruthy();
  });
});
