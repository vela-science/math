# Submission v3 current-state migration

This current branch is a fresh compact prelaunch genesis made with the
branch-built Vela 0.977.0 candidate. It preserves the three intended current
assertions and the two accepted predecessor Claims needed to express the
Erdős 321 and Erdős 94 corrections. It does not claim a scientific change.

## Retain

- five v3 Submissions and Proposals: three current Claims and two exact
  correction predecessors;
- four scoped Verification Records: complementary migration-fidelity checks
  for Erdős 321 and 887, plus independently attributed occurrence-mapping and
  correction-scope checks for the current Erdős 94 successor;
- the seven content-addressed Artifacts, sixteen source-evidence files, and
  four Methods directly used by those records;
- the repository authority key, policy, keyset, Decisions, Events, and exact
  correction relations;
- `refs/heads/rollback/submission-v2-coh-00` at
  `508b39adac51e6823ea0d666e789a1e016b20227`, readable only with the signed
  Vela 0.976.1 release.

## Delete from current state

- every pre-genesis Submission, Verification, Proposal, Claim record,
  Artifact record, Decision, Event, and authority record;
- the old distance-multiplicity verification report and result contract,
  whose exact predecessor record remains available at the rollback ref;
- the three superseded Erdős 94 review Methods; the current v3 checks bind the
  two exact migration-review Methods instead;
- all Submission v2 envelopes and the retired execution-binding field.

Compared with the rollback checkout, the compact state replaces all 29 old
scientific record files with 26 current v3 record files, reduces Verification
Records from six to four, Artifacts from eight to seven, retained evidence
files from eighteen to sixteen, and Methods from five to four. Across those
records, evidence, Methods, and authority files, the current checkout is
16,641 bytes smaller. Git history and the rollback ref are the only legacy
store.

The Erdős 94 predecessor's historical
`distance_multiplicity_double_counting` Verification is not re-attested over
new bytes. Its current successor binds new exact occurrence-mapping and
correction-scope checks, with shared host, source bytes, tooling, and model
provider disclosed; those checks do not establish the mathematics, semantic
equivalence, acceptance, or Standing.
