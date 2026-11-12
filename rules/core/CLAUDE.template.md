# {{PROJECT_NAME}} — editorial constitution

Managed by the `writer-plugin` plugin. Hard rules only; depth lives in the style guide and the artifacts.
Placeholders are filled by the setup skill. Keep this file under 200 lines.

This is a **content workspace**: articles live in `articles/<slug>/`. Each stage writes one artifact (`brief.md`,
`research.md`, `outline.md`, `draft.md`, `final.md`); a read-only gate judges it and returns `PASS` or `BLOCK`.
Local Markdown is the source of truth. A Google Doc is a review copy and never a source.

Style guide for this workspace: `{{STYLE_GUIDE_PATH}}`. Every gate cites a rule ID below; a finding with no ID is not a finding.

## BRF — the brief

- **BRF-1** A specific reader is named.
- **BRF-2** One goal and one call to action (CTA).
- **BRF-3** A primary keyword and the search intent behind it (informational, comparison, how-to, ...).
- **BRF-4** Target length and format are stated.
- **BRF-5** Must-include and must-avoid are stated, even if the answer is "none".
- **BRF-6** The questions the research must answer are listed.

## FACT — facts and sources

- **FACT-1** Every statistic, date, named claim and quote cites a fact ID (`[F7]`) from the fact bank in `research.md`.
- **FACT-2** Every fact has a source URL that resolves, a publisher, a published date and an accessed date. A
  first-party vendor page that shows no published or updated date may say `n/a (live page)` instead of a date.
- **FACT-3** Quotes are verbatim and attributed.
- **FACT-4** A statistic older than the style guide's age limit is flagged, not silently used. A fact from a live page is
  aged by its accessed date, and any later statement of it says "checked <month year>".
- **FACT-5** No claim is stronger than its source.
- **FACT-6** Every question the brief raises is answered by a fact or listed under Open gaps.

## STR — structure

- **STR-1** The promise is stated in the first 100 words.
- **STR-2** Every section traces to the brief's goal.
- **STR-3** Section word budgets sum to the brief's target length, plus or minus 10%.
- **STR-4** One H1 and no skipped heading levels.
- **STR-5** The close delivers the CTA.

## VOI — voice

- **VOI-1** Voice follows the style guide.
- **VOI-2** No banned phrase from the style guide.
- **VOI-3** No AI tells.
- **VOI-4** The reading level meets the style guide's target.
- **VOI-5** No filler and no stacked hedges.

## SEO — search

- **SEO-1** The primary keyword is in the title, in the first 100 words and in at least one H2.
- **SEO-2** The title is at most 60 characters. A client cannot override this.
- **SEO-3** The meta description is 120 to 155 characters. A client cannot override this.
- **SEO-4** The article matches the search intent in the brief.
- **SEO-5** Internal links come from the style guide's link list; external links point to the sources in the fact bank.

## FLOW — workflow

- **FLOW-1** A stage starts only after the previous gate's `PASS` is on disk.
- **FLOW-2** No draft unless `Approved-by:` in the outline has a non-empty value. An empty line is not approval.
- **FLOW-3** Two `BLOCK` verdicts on the same artifact stop the run and hand it to the human.
- **FLOW-4** Gates never edit. The caller saves the verdict to `gates/`.
- **FLOW-5** Fix the artifact, never the style guide, to make a gate pass.
- **FLOW-6** No `final` Doc is labelled publish-ready without `Signed-off-by:` in `final.md`.

## PLG — this plugin

- **PLG-1** No client-specific knowledge enters the plugin repository. Voice, banned words, link lists and audiences
  stay in this workspace's style guide.

## Workspace hygiene

- Never hand-edit a verdict under `articles/<slug>/gates/`; it is the record of what the gate said.
- Never commit credentials, tokens or client data that is not meant for publication.
- A decision made in chat but not written into an artifact does not exist for the gates.
- If an upstream artifact is wrong, stop and say so. Never edit an earlier stage's artifact from a later stage.
- State uncertainty plainly. "I am not sure" beats a confident guess, above all for facts.

## Where things live

- Style guide: `{{STYLE_GUIDE_PATH}}`
- Articles: `articles/<slug>/` — artifacts, `gates/`, `comments/`, `docs.json`
- Rule IDs above are the only vocabulary gates use.

<!-- CLIENT-SPECIFIC RULES: add below this line, keep each one short and say why. -->
