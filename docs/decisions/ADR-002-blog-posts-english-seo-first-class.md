# ADR-002 — Scope: English blog posts, with SEO as a gate concern

- **Date:** 2026-11-12
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (design decisions D2, D3)

## Context
A narrow content type lets the gates be specific instead of generic.

## Decision
The plugin handles blog posts in English only. SEO is a first-class gate concern (rule prefix `SEO`), not an optional checklist.
There is no translation or localisation stage.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| Multi-language or multi-format | Doubles every gate checklist before one slice works |

## Consequences
- Positive: checks such as title length and keyword placement can be scripted.
- Accepted cost: other formats need a new design.

## Revisit when
A real brief needs another language or content type.
