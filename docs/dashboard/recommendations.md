# Recommendation Queue

**Route:** `/recommendations`

The recommendation queue lists all pending recommendations from the AI engine (or the rule-based fallback). Recommendations require farmer approval before any action is taken — the system never acts autonomously.

## What a recommendation shows
Each recommendation card displays:
- **Action description** — e.g., "Irrigate Zone: Tomatoes"
- **Supporting data** — current sensor readings that triggered the recommendation (e.g., VWC: 18%, threshold: 25%)
- **Explanation** — why this action is recommended
- **Source badge** — "AI" (ONNX model) or "Rules" (threshold rule engine)
- **Zone health score** — composite health indicator at time of recommendation

## Approve
Tapping **Approve** sends the command to the hub. For irrigation recommendations: the hub opens the valve and monitors VWC, closing it when the target is reached or the max duration (configurable) is exceeded. The sensor-feedback loop runs automatically after approval — you do not need to manually close the valve.

See [Sensor-Feedback Irrigation Loop](../configuration/automation.md#sensor-feedback-irrigation-loop) for the full behavior.

## Reject
Tapping **Reject** dismisses the recommendation and starts a configurable cool-down window (default: 2 hours) during which no new recommendation of the same type will be generated for the same zone.

## AI Maturity Indicator
A panel at the top of the screen shows the AI engine status:
- Recommendation count and approval/rejection rate per recommendation type
- During cold-start: "Model still learning" message explaining that the AI needs more data
- Toggle: switch between AI recommendations and rule-based fallback. See [AI Settings](settings.md#ai-settings).

## Deduplication
If a pending recommendation of the same type exists for a zone, new duplicates are suppressed until the pending one is resolved.

## Recommendation Back-Off
After a farmer rejects a recommendation, a configurable back-off window (default: 2 hours) prevents the same recommendation type from re-appearing for that zone.

See [Automation Rules](../configuration/automation.md) for the full recommendation lifecycle.
