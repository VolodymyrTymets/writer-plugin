# Research — The Cache-Control header, from max-age to immutable

Slug: http-caching
Brief: `brief.md`

## Questions
| # | Question (from the brief) | Answered by |
|---|---------------------------|-------------|
| Q1 | What does max-age measure? | F1 |
| Q2 | How do no-cache and no-store differ? | F2, F3 |
| Q3 | What does the immutable directive change for a browser? | F4 |
| Q4 | Which standard defines HTTP caching today? | F5, F6 |

## Sources
A first-party vendor page that shows no published or updated date may say `n/a (live page)` in the Published column.
| # | Publisher | URL | Why it is authoritative | Published |
|---|-----------|-----|-------------------------|-----------|
| S1 | IETF (RFC Editor) | https://www.rfc-editor.org/rfc/rfc9111 | The HTTP caching standard itself | 2022-06 |
| S2 | MDN Web Docs (Mozilla) | https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cache-Control | The reference most developers use for the header | 2026-09-17 |

## Fact bank
One row per usable fact. The outline and the draft cite the ID in square brackets.
A first-party vendor page with no published or updated date may say `n/a (live page)` in the published column; the claim
then says "as listed on the page" and the accessed date does the work.

| F# | claim | source URL | publisher | published | accessed | verbatim quote |
|----|-------|------------|-----------|-----------|----------|----------------|
| F1 | max-age makes a response stale once its age is greater than the given number of seconds | https://www.rfc-editor.org/rfc/rfc9111 | IETF (RFC Editor) | 2022-06 | 2026-11-14 | The max-age response directive indicates that the response is to be considered stale after its age is greater than the specified number of seconds. |
| F2 | A response marked no-cache must not be reused for another request until it has been sent for validation and a successful response came back | https://www.rfc-editor.org/rfc/rfc9111 | IETF (RFC Editor) | 2022-06 | 2026-11-14 | The no-cache response directive, in its unqualified form (without an argument), indicates that the response MUST NOT be used to satisfy any other request without forwarding it for validation and receiving a successful response |
| F3 | A response marked no-store must not have any part of the request or the response stored by a cache | https://www.rfc-editor.org/rfc/rfc9111 | IETF (RFC Editor) | 2022-06 | 2026-11-14 | The no-store response directive indicates that a cache MUST NOT store any part of either the immediate request or the response |
| F4 | immutable tells the browser the response will not be updated while it is fresh | https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cache-Control | MDN Web Docs (Mozilla) | 2026-09-17 | 2026-11-14 | The immutable response directive indicates that the response will not be updated while it's fresh. |
| F5 | RFC 9111 defines HTTP caches and the header fields that control cache behavior | https://www.rfc-editor.org/rfc/rfc9111 | IETF (RFC Editor) | 2022-06 | 2026-11-14 | This document defines HTTP caches and the associated header fields that control cache behavior or indicate cacheable response messages. |
| F6 | RFC 9111 replaces the earlier caching standard, RFC 7234 | https://www.rfc-editor.org/rfc/rfc9111 | IETF (RFC Editor) | 2022-06 | 2026-11-14 | This document obsoletes RFC 7234. |

## Competitor coverage
What the top-ranking articles for the primary keyword already say.

| Rank | URL | Angle | What it covers | What it misses |
|------|-----|-------|----------------|----------------|
| 1 | https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Caching | Reference guide | Every directive and the caching model | A short policy a reader can copy for assets and pages |

## The gap this article fills
It turns the directive reference into one policy for fingerprinted assets and one for HTML pages, with the reason for each.

## Open gaps
- none
