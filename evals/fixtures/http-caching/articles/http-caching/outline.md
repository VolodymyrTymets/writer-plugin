# Outline — The Cache-Control header, from max-age to immutable

Slug: http-caching
Brief: `brief.md` · Research: `research.md`

<!-- A human fills this line to approve the outline. Any non-empty value after the colon means approved (FLOW-2);
     an empty line is not approval. The guard-stage-order hook checks this line before it lets draft.md be written. -->
Approved-by: Test Human 2026-11-14

## Thesis
Two policies cover the common cases: cache fingerprinted assets for a long time and mark them immutable, and make HTML pages revalidate with no-cache.

## Title options
1. The Cache-Control header, from max-age to immutable
2. Cache-Control header: a policy for assets and pages

## Intro hook
The first sentence names the cache-control header and what it decides: how long a cache may reuse a response and when it must ask again. The second sentence promises a policy the reader can copy.

## Structure
Word budgets sum to the brief's target length, plus or minus 10% (STR-3).

| Heading | Level | Purpose (traces to the goal) | Key points | Fact IDs | Words |
|---------|-------|------------------------------|------------|----------|-------|
| (intro, under the H1) | — | States the promise so the reader knows they will leave with a policy | What the header decides; the two policies to come | — | 50 |
| What the cache-control header does | H2 | Gives the reader the standard the directives come from, so the policy has a basis | RFC 9111 defines HTTP caches and the header fields that control them; it replaced RFC 7234 | F5, F6 | 80 |
| max-age: how long a response stays fresh | H2 | Explains the one number every policy sets | A response is stale once its age is greater than max-age seconds; quote the definition | F1 | 90 |
| no-cache vs no-store | H2 | Separates the two directives readers confuse, which the brief must include | no-cache allows storing but requires validation before reuse; no-store forbids storing at all | F2, F3 | 100 |
| A fingerprinted asset with immutable | H2 | The worked example the brief must include: the long-lived asset policy | A file name that changes with its content; a long max-age plus immutable; immutable means no update while fresh | F4 | 90 |
| Your two policies | H2 | Lets the reader apply the goal: one policy per kind of response, and the CTA | Assets: long max-age plus immutable; HTML: no-cache, so each reuse is validated first; download the example config | F2 | 50 |

Arithmetic: target 450 → 405 to 495; sum 50+80+90+100+90+50 = 460.

## Keyword map
- **Title:** option 1 and option 2 both contain "Cache-Control header"
- **First 100 words:** the first sentence of the intro
- **H2:** "What the cache-control header does"
- **Secondary keywords:** max-age in its H2; "no-cache vs no-store" as an H2; immutable in the example H2

## Internal and external links
- Example caching config → https://example.com/caching-config (from the style guide's link list)

## Call to action
The last section ends with one sentence asking the reader to download the example server config at https://example.com/caching-config.

## Questions for the human
- none
