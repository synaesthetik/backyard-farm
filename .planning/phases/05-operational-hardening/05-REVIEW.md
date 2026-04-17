---
phase: 05-operational-hardening
reviewed: 2026-04-17T19:28:32Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - hub/api/calibration_router.py
  - hub/api/main.py
  - hub/api/ntfy_router.py
  - hub/api/storage_router.py
  - hub/bridge/alert_engine.py
  - hub/bridge/calibration.py
  - hub/bridge/main.py
  - hub/bridge/ntfy_settings.py
  - hub/bridge/ntfy.py
  - hub/bridge/tests/test_alert_engine.py
  - hub/bridge/tests/test_calibration.py
  - hub/bridge/tests/test_ntfy_settings.py
  - hub/bridge/tests/test_ntfy.py
  - hub/dashboard/src/lib/CalibrationStatusBadge.svelte
  - hub/dashboard/src/lib/CalibrationStatusBadge.test.ts
  - hub/dashboard/src/lib/NtfySettingsForm.svelte
  - hub/dashboard/src/lib/NtfySettingsForm.test.ts
  - hub/dashboard/src/lib/StoragePanel.svelte
  - hub/dashboard/src/lib/StoragePanel.test.ts
  - hub/dashboard/src/lib/types.ts
  - hub/dashboard/src/routes/settings/+layout.svelte
  - hub/dashboard/src/routes/settings/calibration/+page.svelte
  - hub/dashboard/src/routes/settings/notifications/+page.svelte
  - hub/dashboard/src/routes/settings/storage/+page.svelte
  - hub/dashboard/src/routes/zones/[id]/+page.svelte
  - hub/init-db.sql
  - hub/migrations/05-calibration-and-retention.sql
findings:
  critical: 1
  warning: 3
  info: 3
  total: 7
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-04-17T19:28:32Z
**Depth:** standard
**Files Reviewed:** 27
**Status:** issues_found

## Summary

Phase 5 adds calibration management, ntfy push notifications, alert engine with hysteresis, storage/retention UI, and TimescaleDB data retention policies. Overall code quality is solid: Pydantic validates at API boundaries, SQL uses parameterized queries, calibration field updates use an allowlist to prevent injection, datetime handling is consistently timezone-aware, and the migration is properly idempotent with DO/EXCEPTION blocks.

Key concerns: one field-name mismatch between the storage API and the frontend will cause the Storage panel to render blank table names, and the ntfy dispatch logic re-sends notifications for all active alerts on every state change rather than only newly-fired alerts.

## Critical Issues

### CR-01: Storage API returns "table" but frontend expects "tablename" -- StoragePanel renders blank cells

**File:** `hub/api/storage_router.py:56`
**Issue:** The API constructs table info dicts with the key `"table"` (line 56), but the TypeScript `StorageTableInfo` interface declares the field as `tablename` (types.ts:217), and `StoragePanel.svelte` accesses `row.tablename` (line 44). This means every row in the storage table will display `undefined` for the table name column. The `StoragePanel.test.ts` mock data uses `tablename` (line 11), so the test passes, but it does not catch this API contract mismatch.
**Fix:**
Change storage_router.py line 56 to match the frontend contract:
```python
tables = [
    {
        "tablename": row["tablename"],
        "size": row["size"],
        "size_bytes": row["size_bytes"],
    }
    for row in table_rows
]
```
Alternatively, remove the `"schema"` field (line 55) which is not consumed by the frontend. Either way, the key must be `"tablename"` to match `StorageTableInfo`.

## Warnings

### WR-01: ntfy dispatch sends notifications for ALL active alerts on every state change

**File:** `hub/bridge/main.py:326-335`
**Issue:** `_dispatch_ntfy_for_alerts()` iterates `alert_engine.get_alert_state()` and fires a push notification for every active alert. It is called whenever any alert transitions (line 254, 670, 766, 876). If a farm has 5 active alerts and one new alert fires, the farmer receives 6 push notifications (5 stale + 1 new). This will cause notification fatigue and repeated alerts for conditions that have not changed.
**Fix:**
Pass the changed alert(s) into the dispatch function instead of re-broadcasting all active alerts:
```python
async def _dispatch_ntfy_for_alerts(changed_alerts: list[dict]) -> None:
    if not ntfy_settings.is_enabled():
        return
    for alert in changed_alerts:
        asyncio.create_task(send_ntfy_notification(ntfy_settings, alert))
```
At each call site, collect the newly-fired alerts and pass only those. The `evaluate()` method already returns `(changed, is_active)` which can be used to identify which alerts just fired (changed=True, is_active=True).

### WR-02: ntfy_router PATCH allows empty payload to reach bridge, returning opaque 400

**File:** `hub/api/ntfy_router.py:71`
**Issue:** When all fields in `NtfySettingsPatch` are None (e.g., the client sends `{}`), `body.model_dump(exclude_none=True)` produces `{}`. Unlike `calibration_router.py` (line 113-115) which checks for an empty payload before proxying, `ntfy_router.py` sends the empty dict to the bridge. The bridge returns `{"error": "No valid fields provided"}` with status 400, but this round-trips through the proxy, creating a less clear error for the client. The inconsistency between routers also suggests this check was missed.
**Fix:**
Add the same empty-payload guard used in the calibration router:
```python
payload = body.model_dump(exclude_none=True)
if not payload:
    raise HTTPException(status_code=400, detail="No valid fields provided")
```

### WR-03: CalibrationRecordBody uses "offset" but CalibrationPatch uses "offset_value" for the same concept

**File:** `hub/api/calibration_router.py:35,46`
**Issue:** The POST body model `CalibrationRecordBody` names the field `offset` (line 35), while the PATCH body model `CalibrationPatch` names the equivalent field `offset_value` (line 46). In the bridge handler (`main.py:473`), `body.get("offset")` is used for the record path, and `update_calibration_fields` expects `offset_value` in the allowed set. The inconsistency makes it easy for a frontend developer to use the wrong field name in API calls. It also means you cannot use a single form model for both operations without field renaming.
**Fix:**
Consider aligning on one name. Since the DB column is `offset_value` and the PATCH endpoint already uses it, renaming the POST body field would be more consistent:
```python
class CalibrationRecordBody(BaseModel):
    offset_value: float  # renamed from "offset"
    dry_value: Optional[float] = None
    wet_value: Optional[float] = None
    temp_coefficient: float = 0.0
```
Update the bridge handler at `main.py:473` accordingly: `offset = body.get("offset_value")`.

## Info

### IN-01: CalibrationStatusBadge displays "Due in 1 days" (grammar)

**File:** `hub/dashboard/src/lib/CalibrationStatusBadge.svelte:22`
**Issue:** When `days_since` is 13, the label renders "Due in 1 days" (plural). The test at `CalibrationStatusBadge.test.ts:20` explicitly asserts this string, confirming it is intentional, but it reads awkwardly.
**Fix:**
```typescript
const daysLeft = 14 - days_since!;
const label = $derived(
  state === 'overdue'
    ? 'OVERDUE'
    : state === 'due_soon'
      ? `Due in ${daysLeft} ${daysLeft === 1 ? 'day' : 'days'}`
      : `Calibrated ${days_since} ${days_since === 1 ? 'day' : 'days'} ago`
);
```

### IN-02: periodic_calibration_check accesses _active_alerts private attribute

**File:** `hub/bridge/main.py:658`
**Issue:** `periodic_calibration_check` (line 658) and `_handle_record_calibration` (line 495) both access `alert_engine._active_alerts` directly to check whether an alert key exists. This breaks the encapsulation of AlertEngine. If the internal data structure changes, both call sites break.
**Fix:**
Add a public method to AlertEngine:
```python
def is_active(self, alert_key: str) -> bool:
    return alert_key in self._active_alerts
```
Then replace `alert_key in alert_engine._active_alerts` with `alert_engine.is_active(alert_key)`.

### IN-03: asyncio.get_event_loop() deprecation in ntfy tests

**File:** `hub/bridge/tests/test_ntfy.py:33`
**Issue:** `asyncio.get_event_loop().run_until_complete(...)` is used in all four test functions (lines 33, 62, 93, 123). Since Python 3.10, `get_event_loop()` emits a DeprecationWarning when no running loop exists. In Python 3.12+, this may fail outright.
**Fix:**
Use `asyncio.run()` or mark tests as `@pytest.mark.asyncio` with pytest-asyncio:
```python
@pytest.mark.asyncio
async def test_send_ntfy_noop_when_disabled():
    ...
    await ntfy_mod.send_ntfy_notification(settings, alert)
    ...
```

---

_Reviewed: 2026-04-17T19:28:32Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
