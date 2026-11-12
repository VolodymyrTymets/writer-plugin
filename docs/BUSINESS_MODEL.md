# Business model

> Why this project exists. This file is the **tie-breaker** the agent uses when two technically valid options collide.

## What this product is
A Claude Code plugin that takes an article brief to a publish-ready English blog post through actors that write one artifact
each and read-only gates that judge it, with a human approving the outline and signing off the final.

## Ranked goals
1. **Correct gates.** A gate that passes a wrong fact, or blocks on noise, defeats the plugin. Verdict correctness and mechanical
   enforcement (hooks, scripts, structure test) win over everything else.
2. **Ship the Phase 3 vertical slice** (brief, research, outline and their gates) and run it on one real brief.
3. **Polish** (wording of skills, README, ergonomics).

## Non-negotiables (never trade these for speed)
- No client-specific knowledge in this repo (PLG-1).
- Gates never edit (FLOW-4); a decision not written to disk does not count.
- No draft without `Approved-by:` on the outline, no publish-ready final without `Signed-off-by:`.
- Hooks and scripts stay stdlib-only; a hook change ships with a test.

## Explicitly out of scope (this phase)
- Translation or localisation (D3); content types other than blog posts (D2).
- Replying to or resolving Google Doc comments (the connector cannot).
- SERP or keyword-volume data (open question 4).

## Judgement examples
| Situation | Decide this way | Because |
|-----------|-----------------|---------|
| A gate check is noisy but catches real errors | Keep it, narrow its wording | goal 1 |
| Skill text works but reads rough | Ship; fix wording later | goal 2 over 3 |
| A rule can be a hook or a prompt line | Make it a hook | goal 1; "a hook is a mechanism, a prompt is a request" |

## Soft values
Three real findings beat twelve stylistic ones. Say plainly what was and was not verified.
