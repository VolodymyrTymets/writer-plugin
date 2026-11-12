# ADR-003 — Own repo and own marketplace

- **Date:** 2026-11-12
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (design decision D4)

## Context
The plugin shares a shape with `rln-agent` (actor, gate, human approval) but a different domain.

## Decision
`writer-plugin` is its own repo next to `rln-agent`, and its own marketplace (`writer`, plugin `source: "./"`). No code is shared
with `rln-agent`; conventions are copied and then owned here.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| A skill set inside `rln-agent` | Different audience (writers, not developers); couples release cycles |

## Consequences
- Positive: independent versioning and installation.
- Accepted cost: shared conventions can drift between the two repos.

## Revisit when
Two or more plugins need the same gate machinery.
