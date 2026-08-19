# Temporal audit: no earned Core expansion

Quipu correctly distinguishes valid time (when a fact holds in the modeled
world) from transaction time (when a store learned or admitted it). The
comparison question here is smaller:

> What did an external source report when we observed it, and what did this
> Repository admit or correct when its authority acted?

The current artifacts answer both halves without pretending they are one
clock:

- `candidates.json` retains `observed_at` and the source's status as observed.
  That is a derived evaluation fact with `authority_effect: none`; it is not a
  Vela Event or timeless scientific truth.
- a Submission retains producer `emitted_at`; a Verification retains
  `started_at` and `completed_at`; an admitted transition retains its Decision
  performer, authority record, and Event `timestamp`.
- accepted corrections retain both predecessor and successor Claims. Strict
  replay derives their historical and current Standing from admitted Events.
- Git commits retain the exact repository states needed for an as-of replay.

The Erdős 635 comparison exposes an external-status correction: the attempted
proof remained mathematically useful while the novelty/open-status observation
was later shown stale. That correction belongs first to the source observation
and evaluation layer. If a Repository had admitted a Result with a false scope
or novelty assertion, the existing correction path could supersede that exact
Claim while preserving its Event history.

No current question in this bounded set requires querying arbitrary scientific
valid intervals, historical policy-as-data, or a graph-wide valid-time join.
Adding those concepts to Vela Core would duplicate a general bitemporal store
without a demonstrated Vela consumer. The earned action is therefore to keep
`observed_at` in source/projection evidence, keep admission time in current
Vela records, and add no Core schema.

Limitation: Vela is not claimed to answer every “what was scientifically true
at T?” question. A future real Result that cannot be repaired or replayed with
exact source observations and current Events would need a new failing case
before any schema proposal.
