# Trust Score and Anti-Abuse

CityPulse uses two connected internal systems to protect ranking quality:

- `TrustScoreService` estimates how reliable a user's long-term civic participation is.
- `AntiAbuseService` detects manipulation patterns, logs integrity events, and applies short-term safeguards.

These outputs are hidden from regular citizens. They are visible to admins and feed internal ranking and abuse controls.

## Trust Score

The trust score is stored in `user_integrity_snapshots.trust_score` and ranges from `25` to `95`.

Design goals:

- New users start near a neutral baseline instead of being heavily discounted.
- Strong history increases weighting gradually.
- Negative patterns reduce weighting, but do not zero out participation.
- The score changes through repeated behavior, not one isolated action.

### Formula shape

Baseline:

- `55`

Positive factors:

- approved submissions: up to `+14`
- durable usefulness over time: up to `+10`
- meaningful support activity: up to `+8`
- resolved or confirmed issue proxy: up to `+8`
- account age and continuity: up to `+6`
- consistent behavior without suspicious bursts: up to `+5`

Negative factors:

- repeated moderation rejections: up to `-14`
- repeated duplicate posting: up to `-10`
- low-signal feedback against authored issues: up to `-7`
- suspicious burst behavior: up to `-8`
- admin sanctions: up to `-14`

The implementation uses saturating signals rather than linear growth. A user cannot become arbitrarily powerful through volume alone.

## Trust Weight Multiplier

The trust score is converted into a bounded internal multiplier stored in `user_integrity_snapshots.trust_weight_multiplier`.

Bounds:

- minimum: `0.88`
- maximum: `1.16`

This multiplier is used for support weighting inside impact scoring. It is intentionally narrow so trust helps reduce manipulation without making trusted users overwhelmingly dominant.

## Abuse Risk

Abuse risk is stored as:

- `abuse_risk_level`: `low`, `medium`, `high`
- `abuse_risk_score`: `0` to `100`

Signals currently included:

- repeated near-duplicate submissions
- feedback and swipe bursts
- low-quality or recently rejected submissions
- recent integrity events with medium/high severity
- admin sanctions

Risk thresholds:

- `low`: below `25`
- `medium`: `25` to below `60`
- `high`: `60` and above

## Rate Limits and Cooldowns

The anti-abuse service currently applies the following default controls:

- issue submissions: `4` per `30` minutes
- rejected-submission cooldown: `3` rejected reports per `24` hours
- duplicate-spam escalation: hard block after `2` recent high-confidence duplicate attempts within `14` days
- feedback burst guard: `18` feedback actions per `90` seconds
- same-author support concentration warning: `6` supports in `20` minutes
- support tickets: `3` per `60` minutes
- rewrite assist: `6` per `10` minutes for authenticated users

These defaults live in service config dataclasses, not controllers.

## Auditability

Every important integrity signal is logged to `integrity_events` with:

- event type
- severity
- entity reference
- concise operational summary
- structured payload

Reserved privacy-aware hooks are present for:

- `ip_hash`
- `device_fingerprint_hash`

The current implementation keeps those hooks optional and does not require invasive tracking to function.
