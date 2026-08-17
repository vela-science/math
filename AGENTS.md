# Vela Mathematics Program — agent charter

Canonical state is Git history plus the current `.vela/repository.json` manifest. Producers may submit signed evidence directly and record scoped Verification. Only an authorized, attributed Decision changes scientific standing; human and agent performers use the same exact-root and replay checks.

Agents must not copy or export repository-authority credentials, hand-edit canonical records, or describe Verification as acceptance. An agent selected to decide uses `vela review accept|reject --as agent:<name>` and may bind a source-owned `--session-ref`; Repository authority signs the transaction. A Verification method manifest must be tracked, clean, and retained in the current Git commit before `vela verification record`.

```bash
vela status . --json
vela submit --repo . --claim <bounded-claim> --type computational --replayability exact --artifact <path>:<kind> --caveat <limit> --as agent:<name> --json
vela verification record . <vpr_id> --profile <profile> --method <committed-method> --outcome <outcome> --does-not-establish <limit> --as verifier:<name> --json
vela review inbox . --json
vela review accept . <vpr_id> --if-entry-root sha256:... --reason <reason> --as agent:<name> --session-ref <ref> --json
vela replay . --json
```

## What a file's bytes are load-bearing for

A Verification's method manifest is a hash preimage. `sha256(<method file>)`
is the `environment_root` inside the signed DSSE payload of every Verification
citing it, so **editing a retained manifest breaks the record that cites it**
— including to correct a display name or reformat JSON. Fix a manifest by
recording a new Verification against a new manifest, never by rewriting the
old one. The same holds for anything under `evidence/`.

`.gitattributes` protects `records/**` with `-text`. Files under `evidence/`
and `methods/` are preimages too and do not yet carry that protection, so an
evidence file authored with CRLF would be silently rewritten and its digest
would move.

## Binding a Claim to the Problem it is about

A Claim reaches a Problem through a rooted evidence artifact, not through
`provenance[]`. `provenance[]` is a closed source-citation shape, and a Claim
admitted through a signed Submission must carry exactly one entry — the
Submission's own. The subject lives in an occurrence-binding artifact
referenced from `record.evidence[].artifact_path`, whose fixity is checked
against `artifact_root`.

The packet must not contain the successor Claim's root. The Claim references
the packet and the packet would reference the Claim, which has no fixed point;
bind the predecessor's id and root and the corrected assertion instead.

Declaring a subject changes the content-derived `claim_id`, so this is a
signed corrected revision and not an edit. The full crossing is: packet →
corrected Claim → Submission → Proposal → Verifications → Decision → replay.
Existing Verifications and Decisions stay as historical records of the
predecessor and carry nothing over to the new bytes.

Bind only what the Claim covers. A Claim about one bounded variant selects
that occurrence and not every reviewed occurrence its resolver entity holds —
over-selecting is how a bounded identity comes to look like a resolution of
the conjecture.

## Method manifest shapes

`vela.review-method.v1` carries a `reviewer` block — kind, display name,
provider, version, attesting actor — and `vela.verification-method.v1` carries
an `environment` block: `inputs_are_exact_bytes`, `network_required`,
`shared_dependencies`. **Neither is a superset of the other.** Moving a Check
to the newer shape to gain reviewer provenance drops the environment facts
unless the manifest carries both. `display_name` is what the interface shows
as the headline, so name the performer there rather than the role.

## The binary

Verify `vela` by digest, not by version. More than one build reports the same
version and only declared digests are accepted projection generators. Check
`shasum -a 256` and invoke by absolute path; a shell alias may resolve to a
different build than the one intended.
