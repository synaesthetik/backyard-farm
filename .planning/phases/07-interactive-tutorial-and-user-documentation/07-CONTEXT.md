# Phase 7: Interactive Tutorial and User Documentation - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

In-app guided tutorial for new users, full reference documentation for every dashboard feature, and a troubleshooting guide for the 20 most common failure modes. Documentation auto-builds alongside the codebase.

This is the final milestone phase — after this, the platform is fully documented and ready for anyone to set up and use.

</domain>

<decisions>
## Implementation Decisions

### Interactive tutorial (DOC-03)
- **D-01:** Dedicated wizard pages at `/tutorial` route — separate step-by-step screens, not overlay tooltips
- **D-02:** Each step shows what to do with clear instructions, then links to the real dashboard page to perform the action
- **D-03:** Step validation is user self-report — "I did this" button advances to next step. No API state checks.
- **D-04:** Auto-launches on first visit — dashboard detects no tutorial-completed flag in localStorage and shows a welcome screen offering to start. Can be dismissed and accessed later from settings.
- **D-05:** Progress persisted in localStorage — user can close browser and resume where they left off
- **D-06:** Tutorial steps (in order):
  1. Welcome / what you'll learn
  2. First boot setup (Docker Compose, dev-init.sh)
  3. Adding a zone (zone configuration)
  4. Verifying sensor data (check dashboard shows readings)
  5. Running manual irrigation (open/close valve from dashboard)
  6. Setting up coop automation (coop schedule, door controls)
  7. Approving a recommendation (AI recommend-and-confirm flow)
  8. Done / daily operation tips

### Reference documentation (DOC-04)
- **D-07:** Docs built with MkDocs + Material theme — Markdown files in `docs/`, auto-builds to static HTML
- **D-08:** Versioned alongside codebase — `mkdocs.yml` in repo root, `docs/` folder for all content
- **D-09:** Structure covers: every dashboard screen, every configuration option, every alert type, every automation rule
- **D-10:** Include screenshots or annotated UI descriptions for each screen

### Troubleshooting guide (DOC-05)
- **D-11:** Symptom-first organization — farmer searches by what they see ("sensor shows STALE", "door won't close") not by component
- **D-12:** Each failure mode follows: Symptom, Possible Causes, Diagnostic Steps, Resolution
- **D-13:** 20 failure modes covering: sensor offline, stale data, stuck sensor, failed irrigation, stuck door, MQTT disconnection, database full, pH calibration overdue, ntfy not delivering, node offline, power issues, etc.

### Claude's Discretion
- MkDocs theme configuration and nav structure
- Exact screenshot capture approach (automated vs manual descriptions)
- Tutorial page styling (follow existing farm design system)
- Troubleshooting guide ordering within the 20 failure modes
- Whether to include a search feature in docs (MkDocs Material has built-in search)

</decisions>

<specifics>
## Specific Ideas

- Tutorial should feel welcoming for someone who just assembled hardware from Phase 6 docs — connect the physical setup to software setup
- The "Done" step should highlight daily operation: what to check each morning, how to read alerts, when to approve recommendations
- Troubleshooting guide should cross-reference the hardware docs where physical checks are needed (e.g., "sensor offline" links to garden-node.md smoke test)

</specifics>

<canonical_refs>
## Canonical References

No external specs — requirements are fully captured in decisions above and in these project files:

### Project requirements
- `.planning/REQUIREMENTS.md` sections DOC-03, DOC-04, DOC-05 — Documentation requirements
- `.planning/ROADMAP.md` Phase 7 — Success criteria and dependency on Phases 5+6

### Existing docs (content source for reference docs)
- `docs/hardware/README.md` — Hardware docs navigation (cross-reference for troubleshooting)
- `docs/hardware/bom.md` — Component reference
- `docs/hardware/*.md` — All hardware subsystem docs

### Dashboard features (reference doc coverage)
- `hub/dashboard/src/routes/` — All dashboard pages to document
- `hub/dashboard/src/routes/settings/` — Settings pages (AI, Calibration, Notifications, Storage)
- `hub/bridge/alert_engine.py` — Alert types to document
- `hub/bridge/main.py` — Automation rules and loops to document

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Settings sub-navigation layout (`/settings/+layout.svelte`) — tutorial could follow a similar pattern
- Farm design system CSS variables — tutorial pages should use the same theme
- Svelte 5 runes pattern — tutorial state management via `$state`

### Established Patterns
- SvelteKit file-based routing — `/tutorial/+page.svelte` or `/tutorial/[step]/+page.svelte`
- localStorage used for settings persistence (e.g., theme preferences)
- No existing docs framework — MkDocs will be new to the project

### Integration Points
- Tutorial welcome screen triggers from the main layout or home page
- Settings page needs a "Tutorial" link to restart it
- MkDocs config (`mkdocs.yml`) added to repo root
- Docs build step added to CI or documented in README

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-interactive-tutorial-and-user-documentation*
*Context gathered: 2026-04-20*
