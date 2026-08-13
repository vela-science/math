# Source-adapter conformance

`conformance.py` is the reusable, offline contract for source-local Vela
adapters. It checks the disclosure obligations already proven by the Formal
Conjectures adapter: exact native identity and revision semantics, typed roots,
bounded reads, custody and rights, preserved and omitted meanings, unsupported
states, lifecycle behavior, field mutability, reconstructibility, writeback,
and authority nonclaims.

The profile is producer and projection metadata. It is not a Vela protocol
object, does not replace source-native identity, and always has
`authority_effect: none`.

Run the generic hostile suite with:

```bash
python3 -B methods/source-adapters/test_conformance.py
```

An adapter satisfies the contract only when its adapter-specific tests pass an
exact requirement-to-test inventory to `assert_requirement_coverage`. A
well-shaped profile by itself is not conformance evidence.
