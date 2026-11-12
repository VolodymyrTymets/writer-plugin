# G0 checklist

Judge `brief.md` only. Rule IDs allowed at this gate: BRF-1 to BRF-6. A leftover `{{placeholder}}` is a missing field,
so cite the rule of the section it sits in. A BRF finding that blocks research is **blocking**; wording polish is
advisory and rare.

| ID | Blocking when | Passes when |
|----|---------------|-------------|
| BRF-1 | The reader is a group with no role or context ("everyone", "marketers", "users"), or "Already knows" and "Needs to decide or do" are empty | A role and a context are named, and what the reader already knows and what they must decide are stated |
| BRF-2 | There are two or more goals, no goal, no CTA, or several CTAs | One goal and one CTA, with its URL when it has one |
| BRF-3 | No primary keyword, several primary keywords, or no search intent | One primary keyword phrase and one intent (informational, comparison, how-to, ...) |
| BRF-4 | The target length is not a number, or the format is missing | A number of words and a named format |
| BRF-5 | Either field is missing. "none" is a valid answer; an empty field is not | Both stated |
| BRF-6 | No research question, or an item that is a task and not a question ("write about X") | At least one real question the research can answer, tied to the goal |

## Cross-checks
- If `brief.md` states something `brief.source.md` contradicts, cite the BRF rule of that section. A field the source
  never gave must appear under "Assumptions made while normalising", either as an assumption or as
  `<field>: answered by the user, round <n>` (a sourced field); if it is silently invented, that is a finding on
  the rule of its section.
- Ambiguity counts: a field that two readers would fill differently fails its rule.

## Not checked
List what you could not judge: for example, whether the keyword is realistic (no search data is available), or
`brief.source.md` missing.
