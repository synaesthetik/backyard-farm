# Phase 7: Interactive Tutorial and User Documentation — Research

**Researched:** 2026-04-16
**Domain:** SvelteKit in-app tutorial wizard + MkDocs Material reference docs
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Interactive tutorial (DOC-03)**
- D-01: Dedicated wizard pages at `/tutorial` route — separate step-by-step screens, not overlay tooltips
- D-02: Each step shows what to do with clear instructions, then links to the real dashboard page to perform the action
- D-03: Step validation is user self-report — "I did this" button advances to next step. No API state checks.
- D-04: Auto-launches on first visit — dashboard detects no tutorial-completed flag in localStorage and shows a welcome screen offering to start. Can be dismissed and accessed later from settings.
- D-05: Progress persisted in localStorage — user can close browser and resume where they left off
- D-06: Tutorial steps (in order): Welcome, First boot setup, Adding a zone, Verifying sensor data, Running manual irrigation, Setting up coop automation, Approving a recommendation, Done / daily operation tips

**Reference documentation (DOC-04)**
- D-07: Docs built with MkDocs + Material theme — Markdown files in `docs/`, auto-builds to static HTML
- D-08: Versioned alongside codebase — `mkdocs.yml` in repo root, `docs/` folder for all content
- D-09: Structure covers every dashboard screen, every configuration option, every alert type, every automation rule
- D-10: Include screenshots or annotated UI descriptions for each screen

**Troubleshooting guide (DOC-05)**
- D-11: Symptom-first organization — farmer searches by what they see
- D-12: Each failure mode follows: Symptom, Possible Causes, Diagnostic Steps, Resolution
- D-13: 20 failure modes covering: sensor offline, stale data, stuck sensor, failed irrigation, stuck door, MQTT disconnection, database full, pH calibration overdue, ntfy not delivering, node offline, power issues, etc.

### Claude's Discretion
- MkDocs theme configuration and nav structure
- Exact screenshot capture approach (automated vs manual descriptions)
- Tutorial page styling (follow existing farm design system)
- Troubleshooting guide ordering within the 20 failure modes
- Whether to include a search feature in docs (MkDocs Material has built-in search)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOC-03 | Interactive in-app tutorial that walks a new user through first boot, zone setup, sensor verification, manual irrigation, coop automation, and recommendation approval — each step validates completion before advancing | SvelteKit `/tutorial/[step]` routing; localStorage for progress; Svelte 5 `$state` + `$effect` for persistence; self-report "I did this" pattern |
| DOC-04 | Full reference documentation covering every dashboard screen, configuration option, alert type, and automation rule with screenshots and examples | MkDocs 1.6.1 + Material 9.7.6; slate dark scheme; `docs/` directory in repo root; search built-in by default |
| DOC-05 | Troubleshooting guide for the 20 most common failure modes with diagnostic steps and resolution; documentation versioned alongside codebase and builds automatically | Symptom-first Markdown pages in `docs/troubleshooting/`; `mkdocs build` for static HTML; documented `make docs` or npm script for CI integration |
</phase_requirements>

---

## Summary

Phase 7 divides into two independent implementation tracks: (1) a SvelteKit in-app tutorial wizard at `/tutorial`, implemented as a new route group in the existing dashboard codebase, and (2) MkDocs + Material static documentation hosted outside the dashboard but versioned in the same repo.

The tutorial is a straightforward SvelteKit routing exercise — 8 dedicated pages under `/tutorial/[step]`, with localStorage storing current step and completion flag. The dashboard's root layout (`+layout.svelte`) detects the absence of `tutorial_completed` in localStorage on `onMount` and shows a dismissible welcome prompt linking to `/tutorial`. The design system is already established (CSS variables, Inter/Merriweather, dark theme tokens) so the tutorial pages simply use those same variables.

The MkDocs track is a new tool introduction to the project. MkDocs 1.6.1 and Material 9.7.6 are not yet installed — they need a `pip install` step and a `requirements-docs.txt` pinned file. The Material `slate` dark scheme with a custom CSS overriding `--md-primary-fg-color` to match the dashboard's `#4ade80` accent is the correct approach for visual consistency. Built-in search is enabled by default. A `make docs` or documented `pip install && mkdocs build` command in the README serves as the auto-build path; a GitHub Actions workflow is the CI build path but no CI exists yet in the repo.

**Primary recommendation:** Build the tutorial first (pure SvelteKit, no new dependencies), then the MkDocs reference docs and troubleshooting guide as a separate parallel track. The tutorial can be tested with Vitest/Testing Library like all other dashboard components. MkDocs requires Python environment setup as a Wave 0 task.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SvelteKit | 2.57.1 [VERIFIED: package.json] | In-app tutorial routing and pages | Already in use; file-based routing; no new dependency |
| Svelte 5 | 5.55.4 [VERIFIED: package.json] | Tutorial state via `$state`/`$effect` runes | Already in use; runes replace stores for component-local state |
| MkDocs | 1.6.1 [VERIFIED: pypi.org] | Static docs generation from Markdown | Standard Python docs tool; Material theme requires it |
| mkdocs-material | 9.7.6 [VERIFIED: pypi.org, March 19 2026] | MkDocs theme with search, dark mode, nav | Decided by D-07; most-used MkDocs theme; built-in search |
| lucide-svelte | 0.487.0 [VERIFIED: package.json] | Icons in tutorial UI (arrows, checkmarks) | Already in use for all dashboard icons |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @fontsource/inter | 5.1.1 [VERIFIED: package.json] | Tutorial page UI text | Already loaded globally; no additional import needed |
| @fontsource/merriweather | 5.2.11 [VERIFIED: package.json] | Tutorial body copy | Already loaded globally via app.css |
| vitest + @testing-library/svelte | 3.1.1 / 5.2.6 [VERIFIED: package.json] | Tutorial component tests | Already in use; jsdom environment covers localStorage |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `/tutorial/[step]` dynamic route | `/tutorial/+page.svelte` single page with JS step state | Dynamic route is simpler to deep-link, share step URLs, and browser-back correctly |
| localStorage for progress | Server-side session / API endpoint | localStorage is correct choice (D-05 locked); no auth, single user, local-only |
| MkDocs Material | Docusaurus, VitePress | MkDocs locked by D-07; also the Python ecosystem fits the existing Python hub |

### Installation

```bash
# MkDocs (Python side — run once in repo root or in a venv)
pip install mkdocs==1.6.1 mkdocs-material==9.7.6

# Pin versions for reproducibility
pip freeze | grep -E "mkdocs" > requirements-docs.txt
```

No new npm packages needed for the dashboard tutorial track.

---

## Architecture Patterns

### Recommended Project Structure

```
# Tutorial (SvelteKit dashboard — existing src/routes/)
hub/dashboard/src/routes/
├── tutorial/
│   ├── +layout.svelte         # Progress bar + step counter, no TabBar/AlertBar
│   ├── +page.svelte           # Redirect to /tutorial/1 or show welcome
│   ├── 1/+page.svelte         # Welcome — what you'll learn
│   ├── 2/+page.svelte         # First boot setup (Docker Compose, dev-init.sh)
│   ├── 3/+page.svelte         # Adding a zone
│   ├── 4/+page.svelte         # Verifying sensor data
│   ├── 5/+page.svelte         # Running manual irrigation
│   ├── 6/+page.svelte         # Setting up coop automation
│   ├── 7/+page.svelte         # Approving a recommendation
│   └── 8/+page.svelte         # Done / daily operation tips
└── +layout.svelte             # Add tutorial auto-launch check here

# Reference docs (repo root)
docs/
├── hardware/                  # Existing Phase 6 docs (untouched)
├── index.md                   # Platform overview / landing page
├── getting-started.md         # First boot and initial setup
├── dashboard/
│   ├── overview.md            # Home screen
│   ├── zones.md               # Zone cards and zone detail
│   ├── coop.md                # Coop panel
│   ├── recommendations.md     # Recommendation queue
│   └── settings.md            # All settings screens (AI, Calibration, Notifications, Storage)
├── configuration/
│   ├── zones.md               # Zone config options
│   ├── coop.md                # Coop scheduler config (lat/lng, offsets, hard limits)
│   ├── alerts.md              # All alert types, severity, hysteresis values
│   └── automation.md          # Irrigation loop, coop scheduler, recommendation rules
└── troubleshooting/
    └── index.md               # 20 failure modes, symptom-first
mkdocs.yml                     # In repo root
requirements-docs.txt          # mkdocs==1.6.1 mkdocs-material==9.7.6
```

### Pattern 1: Tutorial Step Pages with localStorage Progress

**What:** Each step is a standalone SvelteKit page. Step state (current step, completed flag) lives in a module-level `$state` variable initialized from localStorage in `onMount`.

**When to use:** All 8 tutorial step pages.

**Example:**
```typescript
// hub/dashboard/src/routes/tutorial/+layout.svelte (simplified)
// Source: project pattern — localStorage via onMount (no SSR issue since adapter-node)
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';

  const TOTAL_STEPS = 8;
  const STORAGE_KEY = 'tutorial_step'; // current step 1-8
  const COMPLETE_KEY = 'tutorial_completed';

  let currentStep = $state(1);

  onMount(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) currentStep = parseInt(saved, 10);
  });

  function advance() {
    const next = currentStep + 1;
    if (next > TOTAL_STEPS) {
      localStorage.setItem(COMPLETE_KEY, 'true');
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, String(next));
      currentStep = next;
      goto(`/tutorial/${next}`);
    }
  }

  let { children } = $props();
</script>
```

### Pattern 2: Auto-Launch Welcome Prompt in Root Layout

**What:** The root `+layout.svelte` checks localStorage on `onMount`. If `tutorial_completed` is absent, it shows a dismissible banner offering to start the tutorial.

**When to use:** Only once in `hub/dashboard/src/routes/+layout.svelte`.

**Example:**
```typescript
// Addition to +layout.svelte onMount
// Source: established project pattern (onMount used throughout)
onMount(() => {
  dashboardStore.connect();
  window.addEventListener('farm:toast', handleToast);

  const completed = localStorage.getItem('tutorial_completed');
  const dismissed = localStorage.getItem('tutorial_welcome_dismissed');
  if (!completed && !dismissed) {
    showTutorialBanner = true;
  }

  return () => { /* existing cleanup */ };
});
```

The banner routes to `/tutorial/1` on "Start Tutorial" and sets `tutorial_welcome_dismissed` on "Skip".

### Pattern 3: Tutorial Layout Excludes Main Navigation

**What:** The `/tutorial` route group uses its own `+layout.svelte` that does NOT render `<TabBar>` or `<AlertBar>`. It renders a minimal progress indicator instead.

**When to use:** Tutorial layout only — ensures focused wizard experience.

**Why:** The main `+layout.svelte` wraps all routes including `/tutorial` for the WebSocket connection and toast handler. The tutorial layout only needs to add its own step UI above `{@render children()}`.

### Pattern 4: MkDocs Configuration

**What:** `mkdocs.yml` in repo root, `slate` dark scheme, built-in search enabled, `docs/` as the source.

**When to use:** MkDocs setup (Wave 0 for docs track).

**Example:**
```yaml
# mkdocs.yml — Source: mkdocs-material docs [CITED: squidfunk.github.io/mkdocs-material]
site_name: Backyard Farm Platform
docs_dir: docs
site_dir: site

theme:
  name: material
  palette:
    scheme: slate
    primary: custom
    accent: custom
  features:
    - search.suggest
    - search.highlight
    - navigation.sections
    - navigation.top

extra_css:
  - stylesheets/extra.css  # Override primary color to #4ade80

plugins:
  - search

nav:
  - Home: index.md
  - Getting Started: getting-started.md
  - Dashboard:
    - Overview: dashboard/overview.md
    - Zones: dashboard/zones.md
    - Coop: dashboard/coop.md
    - Recommendations: dashboard/recommendations.md
    - Settings: dashboard/settings.md
  - Configuration:
    - Zones: configuration/zones.md
    - Coop: configuration/coop.md
    - Alerts: configuration/alerts.md
    - Automation: configuration/automation.md
  - Troubleshooting: troubleshooting/index.md
  - Hardware: hardware/README.md
```

```css
/* docs/stylesheets/extra.css */
[data-md-color-scheme="slate"] {
  --md-primary-fg-color: #4ade80;
  --md-primary-fg-color--light: #86efac;
  --md-primary-fg-color--dark: #16a34a;
  --md-accent-fg-color: #4ade80;
}
```

### Anti-Patterns to Avoid

- **Accessing localStorage outside onMount:** SvelteKit runs `+layout.svelte` `<script>` on both server and client. `localStorage` does not exist in the Node.js SSR context. Always wrap in `onMount`. [VERIFIED: established project pattern — all components using browser APIs use `onMount`]
- **Making tutorial steps fetch-dependent:** Steps use self-report validation (D-03). Do not attempt to call dashboard APIs to verify step completion — this would break for users doing setup before hardware is connected.
- **Using the MkDocs `docs_dir` as `hub/dashboard/src/`:** The `docs/` folder is at repo root and should stay there. Hardware docs already live there. Do not nest inside any service folder.
- **Forgetting `$app/environment` mock for tests:** If tutorial components import from `$app/navigation` (e.g., `goto`), the vitest config already mocks this at `src/__mocks__/navigation.ts`. New mocks for `$app/environment` (`browser` variable) should follow the same pattern if needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Static docs search | Custom search index / Algolia integration | MkDocs Material built-in search (lunr) | Built-in by default [VERIFIED: squidfunk.github.io/mkdocs-material]; works offline; no external service |
| Dark mode docs theming | Custom HTML/CSS docs site | MkDocs Material `slate` scheme + CSS var override | 5 lines of CSS vs. building a theme from scratch |
| Progress persistence | IndexedDB, cookies, server-side session | localStorage (D-05 locked) | Single-user, local-only, browser-native; no auth required |
| Step routing state machine | Custom step manager with complex guards | SvelteKit file-based routes `/tutorial/[step]` | Browser back/forward works for free; each step is a URL |
| Docs version tagging | Custom versioning system | Git tags + `mike` MkDocs plugin (optional) | Not required for v1 — single version at repo HEAD is sufficient |

**Key insight:** Both tutorial and docs are content problems, not engineering problems. The hard parts are writing the actual content (20 failure modes, annotated screen descriptions) — not the code infrastructure.

---

## Common Pitfalls

### Pitfall 1: Tutorial Welcome Banner Shows on Every Page Load After Dismissal

**What goes wrong:** The `tutorial_welcome_dismissed` flag is set in localStorage but the banner code checks only `tutorial_completed`. User dismissed without starting; banner re-appears next visit.

**Why it happens:** Two separate localStorage keys — need both in the gate condition.

**How to avoid:** Gate condition: show banner if `!tutorial_completed && !tutorial_welcome_dismissed`.

**Warning signs:** Banner flashes on page load even after clicking "Skip".

### Pitfall 2: Tutorial Layout Double-Wraps Navigation

**What goes wrong:** `/tutorial/+layout.svelte` renders its own header AND the root `+layout.svelte` renders `TabBar` + `AlertBar` — tutorial pages look cluttered.

**Why it happens:** SvelteKit layouts nest by default. Root layout always renders for all routes.

**How to avoid:** The tutorial layout only adds a step-progress bar above `{@render children()}`. It does not attempt to suppress the root layout's output. If the TabBar is visually distracting in tutorial context, apply a CSS class to hide it via a Svelte context or a `$state` flag in the root layout. Alternatively, accept the TabBar — it allows users to navigate away and come back (progress is persisted).

**Warning signs:** Tutorial pages have duplicate navigation bars.

### Pitfall 3: MkDocs `site/` Directory Committed to Git

**What goes wrong:** `mkdocs build` generates `site/` in the repo root. Running it locally commits the entire built site to git.

**Why it happens:** No `.gitignore` entry for `site/`.

**How to avoid:** Add `site/` to `.gitignore` before Wave 0 setup. Docs build is for deployment only, not for committing.

**Warning signs:** `git status` shows hundreds of new HTML/CSS/JS files under `site/`.

### Pitfall 4: localStorage Access During SSR Throws ReferenceError

**What goes wrong:** Tutorial state initialization code runs during SSR because it's in `<script>` top-level, not in `onMount`. Node.js throws `ReferenceError: localStorage is not defined`.

**Why it happens:** SvelteKit with `@sveltejs/adapter-node` does SSR by default. `localStorage` only exists in browser context.

**How to avoid:** Always initialize tutorial state inside `onMount`. Use `$effect` to persist to localStorage when state changes — `$effect` also only runs in the browser.

**Warning signs:** 500 error on `/tutorial` pages during first load; `localStorage is not defined` in server logs.

### Pitfall 5: 20 Troubleshooting Entries Without Cross-References

**What goes wrong:** The troubleshooting guide lists 20 failure modes but doesn't link to the hardware docs for physical diagnosis steps (e.g., "sensor offline" doesn't link to `docs/hardware/garden-node.md` smoke test procedure).

**Why it happens:** Content written in isolation, without checking existing hardware docs.

**How to avoid:** For every failure mode that has a physical component (sensor, actuator, wiring), add a "See also" link to the relevant hardware subsystem doc. The hardware README at `docs/hardware/README.md` shows the structure.

**Warning signs:** User gets to "Diagnostic Steps" for sensor offline and doesn't know where to find the smoke test.

### Pitfall 6: MkDocs Not Pinned in requirements-docs.txt

**What goes wrong:** Someone runs `pip install mkdocs-material` six months later and gets 9.8.x which has breaking nav changes. Docs build breaks silently.

**Why it happens:** No pinned requirements file.

**How to avoid:** Create `requirements-docs.txt` with exact versions (`mkdocs==1.6.1 mkdocs-material==9.7.6`) as a Wave 0 task. Document `pip install -r requirements-docs.txt` in README.

---

## Code Examples

### Tutorial Step Page (Self-Report Pattern)
```typescript
// hub/dashboard/src/routes/tutorial/3/+page.svelte
// Source: established project pattern (settings pages use same $state + onMount)
<script lang="ts">
  import { goto } from '$app/navigation';
  import { ChevronRight, CheckCircle } from 'lucide-svelte';

  const STEP = 3;
  const NEXT_STEP = 4;

  function markDone() {
    localStorage.setItem('tutorial_step', String(NEXT_STEP));
    goto(`/tutorial/${NEXT_STEP}`);
  }
</script>

<svelte:head>
  <title>Farm Tutorial — Step 3: Adding a Zone</title>
</svelte:head>

<div class="tutorial-step">
  <h2 class="step-heading">Step 3: Add Your First Zone</h2>
  <p class="step-body">
    Navigate to <a href="/settings/zones" class="step-link">Settings → Zones</a> and
    create a zone with your garden bed name, soil type, and target moisture range.
  </p>
  <div class="step-actions">
    <a href="/settings/zones" class="action-link">Open Zone Settings</a>
    <button class="btn-primary" onclick={markDone}>
      <CheckCircle size={16} /> I did this
    </button>
  </div>
</div>
```

### Tutorial Welcome Prompt in Root Layout
```typescript
// Addition to hub/dashboard/src/routes/+layout.svelte
// Source: established project pattern (onMount used for WS connect and event listeners)
let showTutorialBanner = $state(false);

onMount(() => {
  dashboardStore.connect();
  window.addEventListener('farm:toast', handleToast);

  if (!localStorage.getItem('tutorial_completed') &&
      !localStorage.getItem('tutorial_welcome_dismissed')) {
    showTutorialBanner = true;
  }

  return () => {
    dashboardStore.disconnect();
    window.removeEventListener('farm:toast', handleToast);
  };
});

function dismissWelcome() {
  localStorage.setItem('tutorial_welcome_dismissed', 'true');
  showTutorialBanner = false;
}
```

### Adding Tutorial Link to Settings
```typescript
// Update hub/dashboard/src/routes/settings/+layout.svelte
// Add tutorial restart tab alongside AI, Calibration, Notifications, Storage
const tabs = [
  { label: 'AI', href: '/settings/ai' },
  { label: 'Calibration', href: '/settings/calibration' },
  { label: 'Notifications', href: '/settings/notifications' },
  { label: 'Storage', href: '/settings/storage' },
  { label: 'Tutorial', href: '/tutorial/1' },  // links out of settings
];
```

### Vitest Test for Tutorial Step
```typescript
// hub/dashboard/src/routes/tutorial/TutorialStep.test.ts
// Source: established project pattern — ZoneCard.test.ts, AlertBar.test.ts
import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';

// localStorage mock (jsdom provides it but starts empty)
beforeEach(() => localStorage.clear());
afterEach(() => cleanup());

describe('Tutorial step advance', () => {
  it('writes next step to localStorage on "I did this"', async () => {
    // render step component, click button, assert localStorage
  });

  it('writes tutorial_completed on final step', async () => {
    // render step 8, click "I did this", assert tutorial_completed set
  });
});
```

---

## Dashboard Routes — Documentation Coverage Map

The reference docs (DOC-04) must cover every route. Map from `src/routes/`:

| Route | Page Title | Doc File |
|-------|-----------|---------|
| `/` | Home / Overview | `docs/dashboard/overview.md` |
| `/zones` | Zones list | `docs/dashboard/zones.md` |
| `/zones/[id]` | Zone detail (sensors, irrigation, calibration) | `docs/dashboard/zones.md` |
| `/coop` | Coop panel (door, feed, water, flock) | `docs/dashboard/coop.md` |
| `/coop/settings` | Coop settings (schedule, lat/lng, offsets) | `docs/dashboard/coop.md` + `docs/configuration/coop.md` |
| `/recommendations` | Recommendation queue | `docs/dashboard/recommendations.md` |
| `/settings/ai` | AI engine toggles + maturity | `docs/dashboard/settings.md` |
| `/settings/calibration` | pH calibration records | `docs/dashboard/settings.md` |
| `/settings/notifications` | ntfy push settings | `docs/dashboard/settings.md` |
| `/settings/storage` | DB stats and purge | `docs/dashboard/settings.md` |
| `/tutorial/*` | Tutorial wizard | Not in reference docs (it documents itself) |

## Alert Types — Documentation Coverage Map

From `hub/bridge/alert_engine.py` `ALERT_DEFINITIONS` [VERIFIED: codebase grep]:

| Alert Key | Severity | Message | Doc Section |
|-----------|----------|---------|-------------|
| `moisture_low` | P1 | "Low moisture — {zone_id}" | `docs/configuration/alerts.md` |
| `ph_low` | P1 | "Low pH — {zone_id}" | `docs/configuration/alerts.md` |
| `ph_high` | P1 | "High pH — {zone_id}" | `docs/configuration/alerts.md` |
| `temp_low` | P1 | "Low temperature — {zone_id}" | `docs/configuration/alerts.md` |
| `temp_high` | P1 | "High temperature — {zone_id}" | `docs/configuration/alerts.md` |
| `feed_low` | P1 | "Low feed level" | `docs/configuration/alerts.md` |
| `water_low` | P1 | "Low water level" | `docs/configuration/alerts.md` |
| `stuck_door` | P0 | "Coop door stuck" | `docs/configuration/alerts.md` + troubleshooting |
| `node_offline` | P0 | "Node offline — {node_id}" | `docs/configuration/alerts.md` + troubleshooting |
| `production_drop` | P1 | "Production drop — eggs below expected" | `docs/configuration/alerts.md` |
| `feed_consumption_drop` | P1 | "Feed consumption drop" | `docs/configuration/alerts.md` |
| `ph_calibration_overdue` | P1 | "pH calibration overdue — {zone_id}" | `docs/configuration/alerts.md` |

---

## 20 Failure Modes — Proposed Ordering

Ordered by frequency of occurrence for a new user (symptom-first per D-11):

1. Sensor shows STALE data (> 5 minutes old)
2. Sensor shows SUSPECT or BAD quality flag
3. Sensor returns static/stuck reading (same value for 30+ readings)
4. Zone shows "No data received" after hardware setup
5. Node shows offline in System Health panel
6. MQTT disconnection — bridge shows no incoming messages
7. Irrigation valve won't open after "Open Valve" command
8. Irrigation valve won't close / zone stuck irrigating
9. Coop door stuck (P0 alert fires, door didn't reach limit switch)
10. Coop door doesn't open/close at sunrise/sunset
11. Recommendation queue empty when sensor is out of range
12. Recommendation appears but "Approve" does nothing
13. pH calibration overdue alert won't clear after calibration
14. ntfy push notification not delivered to phone
15. Dashboard shows blank / no data after fresh install
16. TimescaleDB disk full alert
17. AI domain toggle has no effect on recommendations
18. Production drop alert fires incorrectly
19. Hub not reachable from phone browser (HTTPS/PWA issue)
20. Power loss recovery — nodes reconnect but no data flowing

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MkDocs 0.x config YAML syntax | MkDocs 1.x config with `docs_dir`, `site_dir` keys | MkDocs 1.0 (2019) | YAML structure changed — old tutorials are wrong |
| MkDocs Material `theme: material` minimal config | Material 9.x with `palette.scheme` and `features` list | Material 6+ | Need explicit `scheme: slate` for dark mode |
| Svelte stores (`writable`) for localStorage | Svelte 5 `$state` + `$effect` | Svelte 5 (2024) | `$effect` replaces `store.subscribe` for side effects |
| `$app/env` import for `browser` variable | `$app/environment` import | SvelteKit 1.x | Old `$app/env` removed; use `$app/environment` |

**Deprecated/outdated:**
- `$app/env`: Removed in SvelteKit 1.x. Use `import { browser } from '$app/environment'` instead. [CITED: svelte.dev/docs/svelte/v5-migration-guide]
- MkDocs `pages:` key in mkdocs.yml: Replaced by `nav:` in MkDocs 1.x. [ASSUMED — known breaking change from training data]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | MkDocs `pages:` key is deprecated in favor of `nav:` | State of the Art | Low — affects only mkdocs.yml authoring; easy to fix |
| A2 | `$app/env` was removed and replaced by `$app/environment` in SvelteKit 1.x | State of the Art | Low — project already on SvelteKit 2.57.1; if wrong, just use the older import |
| A3 | The `/tutorial` route will not conflict with any existing SvelteKit route | Architecture | Low — confirmed `src/routes/` has no `tutorial/` directory |
| A4 | Settings nav can include a "Tutorial" link that routes outside `/settings/` | Architecture | Low — SvelteKit `<a href>` works for any route; no guards on settings layout |

---

## Open Questions

1. **Screenshots vs. annotated descriptions for DOC-04**
   - What we know: D-10 says "screenshots or annotated UI descriptions" — either is acceptable
   - What's unclear: Screenshot capture is manual effort for a headless/local system; automated tools like Playwright would add a new dependency
   - Recommendation: Write annotated prose descriptions now (describe what the user sees: widget name, data shown, available actions). Flag screenshots as a future enhancement. This satisfies D-10 without blocking the phase.

2. **Docs auto-build mechanism**
   - What we know: DOC-05 says "builds automatically"; no CI exists in the repo yet
   - What's unclear: "Auto-build" could mean (a) documented `make docs` command, (b) GitHub Actions, or (c) pre-commit hook
   - Recommendation: Create a `Makefile` target `make docs` (or a `scripts/build-docs.sh` wrapper) that runs `pip install -r requirements-docs.txt && mkdocs build`. Document this in README. Treat as "builds automatically when you run the documented command." GitHub Actions can be added in a future phase.

3. **Tutorial access from Settings tab bar**
   - What we know: CONTEXT.md D-04 says tutorial is accessible from settings
   - What's unclear: Does "Tutorial" appear as a tab in the settings tab bar, or as a standalone link elsewhere in the settings page?
   - Recommendation: Add as a tab in the settings tab bar (follows existing pattern of settings sub-navigation). It routes to `/tutorial/1` with a `localStorage.removeItem('tutorial_step')` reset if user wants to restart.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | MkDocs install | Yes | 3.10.17 [VERIFIED: shell] | — |
| pip3 | MkDocs install | Yes | 23.0.1 [VERIFIED: shell] | — |
| mkdocs | Docs build | No | — not installed | Install via `pip install mkdocs==1.6.1` (Wave 0) |
| mkdocs-material | Docs theme | No | — not installed | Install via `pip install mkdocs-material==9.7.6` (Wave 0) |
| Node.js | Dashboard build/test | Yes | v25.3.0 [VERIFIED: shell] | — |
| npm | Package management | Yes | 11.7.0 [VERIFIED: shell] | — |
| vitest | Tutorial component tests | Yes | 3.1.1 [VERIFIED: package.json] | — |

**Missing dependencies with no fallback:**
- `mkdocs` and `mkdocs-material` — must be installed before any docs build task can run. Wave 0 must include a `pip install` task.

**Missing dependencies with fallback:**
- None beyond the above.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 3.1.1 + @testing-library/svelte 5.2.6 |
| Config file | `hub/dashboard/vitest.config.ts` |
| Quick run command | `cd hub/dashboard && npm test -- --run` |
| Full suite command | `cd hub/dashboard && npm test -- --run` (no watch) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOC-03 | Tutorial step advances on "I did this" click and writes to localStorage | unit | `npm test -- --run src/routes/tutorial` | No — Wave 0 |
| DOC-03 | Tutorial auto-launch banner appears when `tutorial_completed` absent | unit | `npm test -- --run src/routes/+layout` | No — Wave 0 |
| DOC-03 | Tutorial completion sets `tutorial_completed` in localStorage | unit | `npm test -- --run src/routes/tutorial` | No — Wave 0 |
| DOC-03 | Tutorial banner dismissed sets `tutorial_welcome_dismissed` | unit | `npm test -- --run src/routes/+layout` | No — Wave 0 |
| DOC-04 | MkDocs build exits 0 (all Markdown valid, no broken links) | smoke | `mkdocs build --strict 2>&1` | No — Wave 0 |
| DOC-05 | All 20 failure modes present in troubleshooting doc | smoke/manual | `grep -c "^## " docs/troubleshooting/index.md` (manual count check) | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `cd hub/dashboard && npm test -- --run`
- **Per wave merge:** `cd hub/dashboard && npm test -- --run && mkdocs build --strict`
- **Phase gate:** Full suite green + MkDocs build clean before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `hub/dashboard/src/routes/tutorial/TutorialStep.test.ts` — covers DOC-03 step advance + localStorage writes
- [ ] `hub/dashboard/src/routes/tutorial/TutorialLayout.test.ts` — covers DOC-03 auto-launch + dismiss logic
- [ ] `requirements-docs.txt` — `mkdocs==1.6.1 mkdocs-material==9.7.6`
- [ ] `mkdocs.yml` — in repo root (Wave 0 setup task)
- [ ] `.gitignore` entry for `site/` — before first `mkdocs build`

---

## Security Domain

Phase 7 is documentation-only and introduces no new API endpoints, authentication changes, or data handling. ASVS categories do not apply.

The tutorial uses localStorage — a client-side browser API — which stores only progress flags (`tutorial_step`, `tutorial_completed`, `tutorial_welcome_dismissed`). These contain no sensitive data, credentials, or PII.

---

## Sources

### Primary (HIGH confidence)
- `hub/dashboard/package.json` — all version numbers for existing dependencies
- `hub/dashboard/src/routes/` — all route paths and existing component patterns
- `hub/bridge/alert_engine.py` — all alert type keys and severity levels
- `hub/dashboard/src/lib/` — all reusable component names
- [pypi.org/project/mkdocs-material/](https://pypi.org/project/mkdocs-material/) — version 9.7.6, release date March 19 2026
- [pypi.org/project/mkdocs/](https://pypi.org/project/mkdocs/) — version 1.6.1, release date August 30 2024
- Shell `python3 --version` / `pip3 --version` — environment availability
- [squidfunk.github.io/mkdocs-material/setup/setting-up-site-search/](https://squidfunk.github.io/mkdocs-material/setup/setting-up-site-search/) — search is enabled by default

### Secondary (MEDIUM confidence)
- [squidfunk.github.io/mkdocs-material/](https://squidfunk.github.io/mkdocs-material/) — MkDocs Material dark theme (slate), nav config, CSS variables for color customization
- SvelteKit docs / migration guide — `$app/environment` replaces `$app/env`, onMount for localStorage

### Tertiary (LOW confidence)
- None — all key claims verified from primary sources.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified from package.json and PyPI
- Architecture: HIGH — based on existing codebase patterns; SvelteKit routing is well-established
- MkDocs configuration: HIGH — verified from official docs and PyPI
- Pitfalls: HIGH — most derived from verified project patterns and official docs
- 20 failure mode list: MEDIUM — derived from reading codebase alert types + CONTEXT.md D-13; completeness depends on user's hardware experience

**Research date:** 2026-04-16
**Valid until:** 2026-07-16 (stable — MkDocs and SvelteKit are mature, slow-moving)
