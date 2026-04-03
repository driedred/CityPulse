# CityPulse Impact Score and Duplicate Detection

## Purpose

CityPulse uses a bounded scoring model so public issue ranking reflects civic priority rather than raw engagement alone. The same intelligence layer also suggests duplicates before submission so support can accumulate on a canonical issue instead of fragmenting across near-identical reports.

## Impact Score

`ImpactScoreService` calculates and caches two outputs for each issue:

- `public_impact_score`: public-facing priority score from `0.0` to `10.0`
- `affected_people_estimate`: rounded public-friendly heuristic for likely affected population

The service also stores an admin-only breakdown with factor weights, normalized signals, raw values, and calculation notes in `issue_impact_snapshots`.

### Inputs

- Unique supporter count
- Trust-weighted supporter count
- Recency decay
- Category severity baseline
- Local density of related nearby reports
- Duplicate aggregation count
- Moderation confidence blended with report quality
- Author trust signal

### Formula

Each factor is normalized to a `0..1` signal, multiplied by a configurable weight, and converted into a `0..10` contribution:

```text
public_impact_score =
  clamp_0_10(sum(weight_i * normalized_signal_i * 10))
```

Current default weights live in `ImpactScoreWeights`:

- `unique_supporters = 0.22`
- `trust_weighted_support = 0.12`
- `recency = 0.14`
- `category_severity = 0.16`
- `local_density = 0.12`
- `duplicate_aggregation = 0.10`
- `moderation_quality = 0.10`
- `author_trust = 0.04`

### Design constraints

- Trust inputs are intentionally bounded so reputation cannot overpower broad community signal.
- Recency uses a half-life decay instead of a hard freshness cutoff.
- Duplicate clustering increases priority when multiple attempted reports converge on one canonical issue.
- Snapshots are recalculated when support changes or cached values age out.

## Affected People Estimate

`affected_people_estimate` is a heuristic, not a census-derived measurement. The public UI should present it as approximate.

Base components:

- Category baseline population assumption
- Weighted support total
- Nearby related report count
- Duplicate cluster size
- Category severity multiplier
- Location-type placeholder multiplier by category slug

High-level formula:

```text
raw_estimate =
  category_baseline
  + weighted_support_total * support_multiplier
  + nearby_related_reports * density_multiplier
  + duplicate_cluster_size * duplicate_multiplier

affected_people_estimate =
  rounded_bucket(raw_estimate * severity_multiplier * location_multiplier)
```

The result is rounded for public display so the UI does not imply false precision.

## Duplicate Detection

`DuplicateDetectionService` evaluates a candidate submission against recent moderation-ready and public issues.

### Signals

- Geographic distance threshold
- Title and description similarity
- Category match
- Time relevance window
- Image similarity placeholder for future extension

### Result classes

- `no_match`
- `possible_duplicates`
- `high_confidence_duplicate`

Each match returns:

- `existing_issue_id`
- `similarity_score`
- `reason_breakdown`
- `distance_km`
- `text_similarity`
- `category_match`
- `recommended_action`
- `image_similarity`

### Recommended actions

- `support_existing`: use when the candidate strongly overlaps with an existing issue
- `review_before_submit`: use when overlap is meaningful but not definitive
- `submit_new_issue`: reserved for future expansions when the service wants to affirm distinct evidence

## Support Existing Flow

When a user supports an existing issue instead of posting a duplicate:

1. The platform records a support signal with duplicate-safe uniqueness constraints.
2. The canonical issue score is refreshed.
3. An optional duplicate analytics link is stored in `issue_duplicate_links`.
4. The citizen remains free to submit anyway if they have distinct evidence.

This keeps the product focused on prioritization and operational clarity instead of maximizing post volume.
