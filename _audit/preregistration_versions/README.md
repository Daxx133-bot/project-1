# Preregistration version archive

Every superseded version of `PREREGISTRATION.md`, kept so that any claim about "what was
preregistered, and when" can be checked rather than taken on trust.

| File | Date | Status | What changed |
|---|---|---|---|
| `PREREGISTRATION_v1.md` | 2026-09-23 | superseded | First draft. H1 predicted blast radius from the fan-out-corrected hybrid metric (out-degree). `T_rec` measured from fault injection. Single blast-radius total. |
| `PREREGISTRATION_v2.md` | 2026-09-25 | superseded | H1 reversed to \|ancestors\| after the pilot falsified the direction. Gateway exclusion, three-column blast radius, `T_rec` from fault removal, per-fault-type indicators, exact permutation tests. Left Q1/Q2/Q3 open. |
| `PREREGISTRATION_v3_LOCKED.md` | 2026-09-26 | **LOCKED** | Q1/Q2/Q3 closed. `ancestor_count` is the primary predictor; H1b added (hybrid hypothesised anti-predictive); CPU dropped; HR held-out/directional only; per-service metric semantics fixed; FDR family 44 confirmatory (kill) + 44 replication (latency), corrected separately. |

The live working copy is `PREREGISTRATION.md` at the repository root. It is identical in
substance to the locked v3 copy; the locked copy is the one to cite, and it carries the
commit hash of the code state the campaign ran against.

v1 was reconstructed from git (`git show fd489f4~1:PREREGISTRATION.md`) because it was
only ever superseded in place, never archived at the time.
