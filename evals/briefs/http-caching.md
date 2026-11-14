# Brief — How Cache-Control decides what a browser reuses

Slug: http-caching
Source: `brief.source.md` (the brief as it was supplied, kept unchanged)

## Reader (BRF-1)
- **Who:** a backend developer at a small software company who runs their own web servers
- **Already knows:** what an HTTP header is and how to set one in their server config
- **Needs to decide or do:** choose Cache-Control values for static assets and for HTML pages

## Goal and call to action (BRF-2)
- **Goal:** the reader can pick a Cache-Control policy for each kind of response and explain why
- **CTA:** download the example server config at https://example.com/caching-config

## Keyword and search intent (BRF-3)
- **Primary keyword:** cache-control header
- **Search intent:** informational
- **Secondary keywords:** max-age, no-cache vs no-store, immutable

## Length and format (BRF-4)
- **Target length:** 1200 words
- **Format:** explainer

## Must include and must avoid (BRF-5)
- **Must include:** the difference between no-cache and no-store; one worked example for a fingerprinted asset
- **Must avoid:** CDN vendor comparisons

## Questions the research must answer (BRF-6)
1. What does max-age measure, and from when?
2. How do no-cache and no-store differ?
3. What does the immutable directive change for a browser?
4. Which standard defines HTTP caching today?

## Assumptions made while normalising
- none
