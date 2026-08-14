# App Feedback (v1) — relation to Trace

Soft in-app feedback (thumbs + optional short text) is **not** usage telemetry.

| | `Trace.track` | Feedback submit |
|--|---------------|-----------------|
| Local consent (`trace_consent.json`) | **Required** | **Not used** |
| User can disable | Settings → 使用统计 | Settings / popup → stop *prompts* |
| Once user taps Send | N/A | **POST immediately** (no permission gate) |
| Endpoint | `POST /api/v1/traces` | `POST /api/v1/feedback` |

Implementation: [`core/infra/feedback`](../../feedback/) (`Feedback.submit`).  
Drupal contract: `new_tea_tools/docs/FEEDBACK_API.md` on the website repo.

Nav “反馈” opens the public contact page and never hits either API.
