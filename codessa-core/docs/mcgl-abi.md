# MCGL: Cognitive Event ABI

MCGL is the stable boundary between an unpredictable external world and Codessa's deterministic epistemic kernel. It is **not** a news schema or an LLM output format. Every domain adapter—GitHub Releases, a research feed, a customer request, a music release, or an IoT sensor—must compile its observation into this ABI before kernel processing.

```text
World -> RawEvent -> Normalizer -> CanonicalEvent -> EpistemicAssessment
                                                -> ClaimGraphEvent -> kernel projections
```

## Boundary rules

1. **The kernel accepts `CanonicalEvent` only.** Connectors and normalizers are replaceable adapter code; they cannot write claims or actions directly.
2. **Evidence is immutable.** Retain the raw payload outside the normalized record and bind it with `raw_payload_hash`. `CanonicalEvent.content_hash` binds the normalized content used for later derivation.
3. **Claims are derived, never embedded in observations.** A source item may contain many claims or none. Claim extraction produces append-only `ClaimGraphEvent` records that point to their source event IDs.
4. **Assessments are dimensions, not truth.** `EpistemicAssessment` keeps evidence, trust, novelty, agreement, freshness, relevance, contradiction, and impact separate. An analyzer may contribute metadata, but it is not authoritative evidence.
5. **Replay requires versions.** Normalizers, extractors, and assessors identify their versions. Reprocessing emits new derived events rather than mutating old ones.
6. **Actions are downstream.** Goal matching and skills may consume assessed claim events, but an adapter or model cannot bypass the kernel and execute an action.

## Contracts

| Contract | Purpose | Required provenance |
| --- | --- | --- |
| [`canonical-event.schema.json`](../schemas/mcgl/canonical-event.schema.json) | A normalized observation that crosses the ABI. | Raw-event ID, raw payload hash, normalizer and version. |
| [`epistemic-assessment.schema.json`](../schemas/mcgl/epistemic-assessment.schema.json) | A replayable, multi-dimensional evaluation of one observation. | Assessor and version; evidence references. |
| [`claim-graph-event.schema.json`](../schemas/mcgl/claim-graph-event.schema.json) | An append-only assertion, support, opposition, retraction, or supersession in the claim graph. | Canonical event IDs, extractor and version. |

The included [`github-release.canonical-event.json`](../schemas/mcgl/examples/github-release.canonical-event.json) demonstrates the GitHub Releases adapter target without making GitHub-specific fields part of the kernel contract.

## Hypotheses

A hypothesis is not an input replacement for evidence. It is a projection over competing `ClaimGraphEvent` records, with supporting and opposing claim references, a status, and a reproducible confidence calculation. It belongs after claim extraction and assessment; its storage model should be added only once the claim graph contract has been exercised by a real connector.

## Compatibility policy

- `schema_version` is a required ABI version. Version `1.0` disallows undeclared fields so consumers do not silently rely on adapter-specific data.
- Additive changes require a new compatible schema version and explicit consumer support.
- Breaking changes require a new major version; older events remain valid historical evidence.
- Domain-specific fields stay in the raw payload or an adapter namespace outside the kernel ABI.
