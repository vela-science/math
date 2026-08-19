# Primary-source product audit

Frozen 2026-08-19 from the FAR paper/code and anonymous live ProbXiv routes.
“Observed” means visible in those primary sources. “Inference” is called out
and is not stored as source fact.

## FAR

Exact sources are in `audit.json`. The public code is one unsigned commit with
no tag or release. The paper and code have different rights grants; the absent
pilot corpus and source-paper bytes are not covered merely because the code is
Apache-2.0.

### Researcher journey and states

Observed journey:

1. provide an Arrow corpus with one paper `text` field and a research direction;
2. configure three provider endpoints/keys and the external `opencode` CLI;
3. run `label → extract → check → solve → judge → grade`;
4. inspect local JSONL and per-candidate Markdown workspaces;
5. have mathematicians inspect selected `TYPE2`/`TYPE3` artifacts.

Observed Find state includes paper selection, an extracted unresolved
statement, `open|solved|invalid` status evidence, and importance/difficulty
estimates. Attempt emits `KNOWN|NEW|FIX|NONE`; automated judgement emits
`PASS|FAIL|KNOWN`; significance emits `KNOWN|TYPE1|TYPE2|TYPE3`. Human review
exists in paper prose, not a public record schema.

Observed evidence includes source metadata/text, statement/section, status
citations `{title,url,claim}`, natural-language attempt, judge and grader
rationales, durations, and early-stage model logs. The generic output does not
bind an authenticated performer, exact per-Result model/provider, corpus
digest, executable proof, formal check, authority identity, or signed Decision.

### Identity, correction, and loss

Observed attempt identity is positional `(row_index,candidate_index)`.
`judge_id` is a pass ordinal, not an authenticated verifier principal. The
paper used three GPT-5.5 xhigh judge passes; the public script defaults to one.
The pipeline can discover `KNOWN` during several stages and `FIX` a defective
statement. Later statistical analysis excludes candidates reclassified by a
status recheck.

Inference: corpus reordering changes positional identity. Separate model
passes do not establish independent people, institutions, credentials,
providers, or tools. A later file or paper can explain a correction, but the
observed format cannot replay it as an attributed state transition.

Observed interchange is Arrow plus unversioned JSONL/Markdown. The repository
ignores corpus, outputs, logs, and workspaces, has lower-bound dependencies
rather than a lock, and publishes none of the pilot data. A clean clone cannot
reconstruct the 51,110-paper corpus, 4,717 attempts, 598 accepted automated
results, or 77 recommendations. Retained local JSONL stays readable after a
provider loss, but exact pilot reconstruction does not follow from public Git.

## ProbXiv

The site was inspected in a real browser anonymously. The live home exposed
1,183 Problem pages and the exact counts retained in `audit.json`. The FAR
collection exposed 597 entries while the paper reports 598 automated-judge
acceptances; the audit records the divergence without guessing why.

### Reader and contributor journey

Observed reader journey: search or filter the public registry, open a stable
Problem URL, inspect source/status, follow an anchored attempt, and distinguish
machine judgement, formal check, and human involvement. Anonymous reading is
open. Participation offers Google sign-in or a 15-minute email magic link and
asks for an institutional address.

Observed identity behavior separates the named tool from ProbXiv account
credit. FAR attempts credit no account. A tool name is not a person. No
attributed authority principal, Decision, Event, or status-history replay is
exposed on the sampled routes.

Observed states include `open|solved|disproved|partial|candidate|variant|retracted`
and judgement levels `LLM-verified|unverified|formalized`. The product copy also
names `human-endorsed`, but the anonymous filter exposed no current option or
count. Attempts are separate comment records with anchors such as
`#attempt-1`.

### Evidence, correction, and loss

ProbXiv already does several things well: an LLM judgement says it is not a
proof or a person; a Lean-backed page scopes compilation to the formalization
and disclaims statement fidelity; attempts do not silently become reviews.
Erdős 7 remains resolvable after retraction with the disputed material
preserved. No duplicate status/filter, corrects/supersedes relation, or
historical status-event stream was observed. Whole-word search for `duplicate`
returned no match.

Observed delivery is server-rendered Next.js on Vercel with private/no-store
responses and opaque build ID `pFL34NvMDdnDPDQcowdr6`. `/api` returned 404,
robots excluded `/api/`, and requesting JSON from a detail page returned HTML.
No JSON-LD, public API/export documentation, site source repository, semantic
version, terms, or content license was linked from sampled home, collection,
detail, and sign-in routes.

Inference: upstream links help preserve scientific occurrence identity, but
the observed public contract cannot reconstruct ProbXiv accounts, comments,
judgements, or editorial statuses after provider loss. Private backups may
exist. Because no public content license was observed, this fixture retains
only URLs, dates, short factual labels, character counts, and digests.

## Quipu checkpoint

Quipu supplies a useful challenge: separate world-valid time from store
transaction time, and replay decisions against the rules in force. Its paper
reports 50/50 accepted verdicts re-derived as of their instant; the six denial
checks retain rules-in-force while rejected deltas are discarded. The
benchmark, adapter, and degradation transforms are author-provided, and the
paper calls cross-corpus comparisons indicative.

That is evidence to monitor, not evidence of a current Vela Result failure.
`TEMPORAL_FINDING.md` applies the question to this bounded comparison and finds
no earned Core schema change.
