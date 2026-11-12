# ADR-001 — Local Markdown is the source of truth; Google Docs are review copies

- **Date:** 2026-11-12
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (design decision D1)

## Context
Reviewers want Google Docs and comments; hooks and gates must read files deterministically. The Drive connector can create
converted Docs but `update_file` changes metadata only, and the connector is not present in every session.

## Decision
Every artifact lives as Markdown in the content workspace. Each is also published as a Google Doc copy for review. Hooks and
gates read only the local files. A revision is a new Doc, recorded in `docs.json`.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| Google Docs as source of truth | Hooks and gates could not read it offline or reliably; the connector cannot update content |

## Consequences
- Positive: the workflow runs with no connector; gates are deterministic.
- Accepted cost: reviewer comments must be pulled back by a sync step.
- Follow-ups: Markdown fidelity of the Doc copy (open question 1).

## Revisit when
The connector supports content updates and comment replies.
