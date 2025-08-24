
---

```markdown
<!-- File: docs/testing/acceptance-criteria.md -->
---
title: Acceptance Criteria — Multi-Agent Factory
owner: QA Lead (Name • handle@domain)
version: 1.0
last_reviewed: 2025-08-13
next_review: 2025-10-01
status: normative
scope: repo-wide
---

# Acceptance Criteria

## Functional Criteria
- All user stories have corresponding BDD scenarios with unambiguous preconditions and postconditions.
- API contracts (schemas, status codes, error shapes) conform to the OpenAPI spec committed in the repo.
- Cross-agent workflows complete with observable state transitions and idempotent retries.

## Non-Functional Criteria
- **Performance:** API p95 < 200 ms under nominal load; throughput > 1000 tasks/min (locust profile “nominal”).  
- **Reliability:** Task failure rate < 0.1% over a 24-hour synthetic run.  
- **Security:** No critical issues from Bandit/Safety/ZAP; JWT/RBAC paths verified.  
- **Usability:** Error messages actionable; docs examples runnable as written.

## Exit Conditions
- Green CI across unit → integration → system → acceptance stages.
- Coverage thresholds met; zero critical vulnerabilities.
- Signed test report with risks/deviations, if any.

## Evidence
- CI artifacts: coverage report, ZAP/Bandit/Safety outputs, Locust CSV/HTML, test logs.
