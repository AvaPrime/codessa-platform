# Codex status

## 2026-09-15 — MCGL Cognitive Event ABI

- Added the first versioned MCGL schemas for canonical observations, epistemic assessments, and derived claim-graph events.
- Documented the RawEvent → CanonicalEvent → ClaimGraphEvent boundary so source adapters and analyzers cannot bypass the deterministic kernel.
- Next: implement a GitHub Releases normalizer that persists raw payloads and emits validated `CanonicalEvent` records into the selected E-COS store.
