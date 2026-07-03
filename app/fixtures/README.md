# Fixtures

Synthetic placeholder data shaped exactly like the `worldcup26.ir` API
responses (`games.json`, `teams.json`, `groups.json`) — 48 teams across 12
groups, a full group stage, and a chained knockout bracket (R32 → R16 → QF →
SF → Final) using the same `"Winner Match N"` / `"Loser Match N"` label
convention the real API uses.

Useful when `worldcup26.ir` is unreachable (it 502'd for a while during
development) and you still want to look at the app with realistic data.

Regenerate with:

```
python app/fixtures/generate.py
```

Not wired into any app yet — the apps in `app/` all call the live API
directly. To point an app at these files instead, swap the `requests.get(...)`
calls in its `@reactive.calc` data functions for `json.load(open(...))` on
these files.
