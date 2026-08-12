# Formal Conjectures cross-layer conformance

This directory holds source-local conformance inputs for the Formal
Conjectures-to-Vela path. They are evaluation and adapter requirements, not
Vela protocol objects and not Math Repository state.

`do-not-collapse.v0.1.json` is the composed matrix required by the ecosystem
convergence execution contract before `MATH-01` or `WEB-03` can freeze. It
keeps source observations, activity preparation, signed portable objects,
Repository authority, and derived reads in separate domains. The matrix has
`authority_effect: none`; passing it cannot create a Verification, Decision,
Event, or Standing.

Matrix root:
`sha256:81c088354d7aa247aa50c655566a5971aa21ccbaded1823867357b6a3c7735b6`.

The matrix has two acceptance layers. Eight anti-collapse rules keep source
results, activity, portable signed objects, human authority, and derived reads
separate. Nine adapter requirements additionally freeze unsupported-version
refusal, full field/schema-typed roots, exact-source drift, bounded complete
reads, copied-versus-referenced custody, interpreter identity, native
licensing/access and redaction, reconstructibility/loss, and source
deletion/mutability behavior. They are requirements for `MATH-01` and
`WEB-03`; this file does not claim those future consumers are implemented.

Custody is not homogenized. Core and Math exact commits are public. The
reviewed Math tree declares no repository-wide license, so public visibility
does not imply reuse rights. The reviewed Web commit is private and can be
checked only by an authorized reviewer; no private Web source is copied into
this public packet. Its later `WEB-03` gate must therefore prove the real
parser, mapper, renderer, and refusal paths inside that private Repository.

Run the offline check with:

```bash
python3 -B evidence/formal-conjectures/conformance/test_do_not_collapse.py
```
