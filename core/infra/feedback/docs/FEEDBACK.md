# Feedback module (v1)

Anonymous soft feedback from the NTQ app to Drupal `POST /api/v1/feedback`.

## Consent model

- **Does not** read or require `Trace.consent` / `Trace.track` permission.
- Users may disable **prompts** anytime (`feedback_prefs.json`).
- When the user submits (thumbs / text), the client POSTs with no local gate.

## Public API

```python
from core.infra.feedback import Feedback

Feedback.submit(rating="up", text="可选", source="popup")  # bool
Feedback.note_task_success(source="scan")  # {"should_prompt": bool, ...}
Feedback.snooze_prompt()
Feedback.disable_prompts(source="popup")
Feedback.get_prefs()  # dict
Feedback.set_prompts_disabled(disabled=True, source="settings_ui")
```

Default ingest URL: `FeedbackDefaults.TARGET_URL`  
(`https://www.new-tea.cn/api/v1/feedback`).

Wire schema and Flood rules: see Drupal `new_tea_tools/docs/FEEDBACK_API.md`  
and the short note under `core/infra/trace/docs/FEEDBACK.md`.
