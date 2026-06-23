# External Data Review Gate - 2026-06-24

Purpose: ensure externally researched player, manager, tactical, substitution, and national-strength data improves simulation accuracy without creating false certainty or starving sparse teams of usable context.

## Review Stance

Do not treat the gate as a simple pass/fail filter.

The correct Codex posture is:

1. Preserve signal.
2. Label uncertainty.
3. Separate current-field candidates from future-engine candidates.
4. Only apply data changes after a source-backed spec and benchmark check.

Sparse teams should not be punished just because fewer sources exist. Weak evidence may still be useful as provisional context, UI uncertainty, or a review question.

## Use Tiers

The validation script groups candidates into:

- `ready_for_codex_review`: strong enough to consider in a future data-changing spec.
- `provisional_context`: useful for judgment, but not enough for direct seed/rating changes.
- `review_question`: keep the signal, but require more evidence before use.
- `future_engine_candidate`: valuable only after the simulation engine gains a field or behavior for it.
- `insufficient_detail`: too thin to act on, but still kept for traceability.

## Accuracy Impact Questions

For each candidate, Codex should ask:

- Does this map to an existing simulator input?
- If yes, would changing that input plausibly affect match probabilities, lineup quality, event flow, or user trust?
- If no, is it still valuable as a future feature, such as manager-specific substitution behavior?
- Is the source tier strong enough for the field?
- Is the claim current enough under `metadata.json` freshness policy?
- Could this introduce overfitting, celebrity bias, or federation/news-source bias?
- Would it help a sparse team avoid generic/default behavior?

## Do Not Over-Filter

Rejected automatic data changes are not the same as useless data.

Examples:

- A Tier B tactical article should not directly rewrite `press_intensity`, but can support a tactical-review candidate.
- A weak substitution-pattern note should not change the engine, but can justify a future substitution-tendency feature.
- Sparse-team national-strength context may be low confidence but still better than leaving a team entirely generic.

## Current Tool

Run:

```powershell
cd backend
.\venv\Scripts\python.exe scripts\validate_external_data_verification_report.py reports\external_data_verification_candidates_2026-06-24.json --out reports\external_data_verification_validation_2026-06-24.json
```

The output is a triage report, not a final judgment.
