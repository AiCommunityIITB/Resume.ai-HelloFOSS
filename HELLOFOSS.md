# Reviewed HelloFOSS contribution topics

These are the ten topics reviewed by the project manager. They are proposals, not implemented features; coordinate with maintainers before selecting a task.

| # | Topic | Type |
|---|---|---|
| 1 | Improve layout scoring with alignment, spacing, hierarchy, density, page balance and interpretable component feedback | Pipeline |
| 2 | Improve domain detection, preserve experience evidence, fix fallback thresholds, evaluate confidence and mixed-domain cases | Bug / ML |
| 3 | Include copyable, correctly escaped LaTeX `\item` code beside each suggested resume pointer | Feature |
| 4 | Job-description Evidence Map: link requirements to supporting resume bullets and distinguish uncertain/missing evidence | Feature |
| 5 | Resume Revision Lab: compare draft revisions with originals under a consistent model/rubric version | Feature |
| 6 | Analyze once and reuse owner-isolated results keyed by content/model/prompt/corpus versions | Pipeline |
| 7 | Persist resumable analysis jobs with cancellation, reconnection and retry-only-failed-stage behavior | Pipeline |
| 8 | Unify four-dimension score parsing and normalization across endpoints | Bug |
| 9 | Join similarity-search embeddings to project records by stable IDs rather than query position | Bug |
| 10 | End upload processing correctly on stream errors, cancellation and premature EOF | Bug |

Each task needs a scoped acceptance checklist and synthetic regression tests. No real provider credentials are required for the isolated unit-test path. Runtime embeddings may be generated privately; approved numeric model artifacts are already retained in this snapshot.
