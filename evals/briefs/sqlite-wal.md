# Brief — When to turn on SQLite's write-ahead log

Slug: sqlite-wal
Source: `brief.source.md` (the brief as it was supplied, kept unchanged)

## Reader (BRF-1)
- **Who:** an application developer who embeds SQLite in a desktop or mobile app
- **Already knows:** basic SQL and how to open a SQLite database from their language
- **Needs to decide or do:** decide whether to switch their database to WAL mode

## Goal and call to action (BRF-2)
- **Goal:** the reader knows what WAL mode changes for readers and writers, and when it does not fit
- **CTA:** try the WAL checklist at https://example.com/wal-checklist

## Keyword and search intent (BRF-3)
- **Primary keyword:** sqlite wal mode
- **Search intent:** informational
- **Secondary keywords:** journal_mode, checkpoint, concurrent readers

## Length and format (BRF-4)
- **Target length:** 1000 words
- **Format:** explainer

## Must include and must avoid (BRF-5)
- **Must include:** the PRAGMA that turns WAL on; the case where WAL does not work (network filesystems)
- **Must avoid:** benchmarks against other databases

## Questions the research must answer (BRF-6)
1. What does WAL mode change about how writes reach the database file?
2. Can readers and a writer work at the same time in WAL mode?
3. What is a checkpoint, and when does it run?
4. In which setups does the SQLite documentation advise against WAL?

## Assumptions made while normalising
- none
