---
name: define-spec
description: Use when the user wants a piece of work described before it is carried out - "write a spec for X", "define a spec", "spec this out before we build it", "write a brief for investigating which queue we should use", "spec the rewrite of the getting started guide", "spec the migration to the new store", "spec the skill that formats changelogs", or "the spec needs to cover Y as well". Classifies the work as code, documentation, research, skill, or operations, interviews the user until every required section of that kind is decided, then writes a numbered spec file (by default docs/specs/<n>-<name>/task.md, overridden by whatever the project's own rules say). Stops at the spec and does not carry it out. Not for implementation requests, for reading an existing spec, or for READMEs, ADRs, changelogs, and pull request descriptions.
---

# Define a spec

Turn a request into a complete, numbered spec file. The spec is the contract later work is
verified against, so nothing in it may be a guess, and the sections have to fit the kind of work.

Read `reference.md` once the genre is known: it holds the classification rules, the per-genre
question banks, convention detection, numbering, and the pre-write check. Write the file from
`templates/<genre>-spec.md`.

## Genres

The deliverable decides the genre, not the topic. "Research the migration" is research, because
the output is an answer; "do the migration" is operations, because the output is a changed system.

- **code** - features, bug fixes, refactors. Output is working software.
- **documentation** - guides, references, tutorials, restructuring existing docs. Output is prose.
- **research** - investigations, evaluations, comparisons, spikes. Output is an answer not known
  yet.
- **skill** - agent skills. Output is a skill, and its activation contract is the hard part.
- **operations** - migrations, rollouts, infrastructure and pipeline changes. Output is a changed
  running system, and reversibility is the hard part.

## Steps

1. **Restate the subject** in one sentence. If the request names no concrete piece of work, ask
   what it is before anything else.

2. **Classify the genre and say so** before interviewing, so a wrong pick is caught before the
   wrong questions get asked. Ask instead of guessing whenever the subject reads both ways -
   "spec the migration guide" is documentation or operations, "spec the changelog script" is code
   or skill. If a subject fits no genre, use code and say that this was a fallback. Never invent a
   sixth genre, and never merge two into one document.

3. **Resolve this repository's conventions.** Project rules override the defaults below. Check the
   repository's agent instructions and contributing docs, and look at any existing spec directory,
   for a stated spec location, filename, numbering scheme, or section set, and adopt what is
   stated. Defaults where nothing is:
   - `docs/specs/<n>-<kebab-name>/task.md`
   - `<n>` is a plain integer; first spec is `1`, otherwise the highest existing number plus one
   - `<kebab-name>` is short and verb-first, e.g. `4-add-audit-log`

4. **Create or update?** Look for an existing spec on the same subject. If one exists, amend it,
   keep its number, and keep its genre unless the subject itself changed - never add a second spec
   for the same subject. Ask if it is unclear whether the request extends an existing spec or
   opens a new one.

5. **Interview in rounds** using the question bank for the classified genre in `reference.md`. Ask
   in batches, in the user's own words, about the sections still undecided. Keep going while any
   required section of that genre would have to be invented. An item may stay open only if the
   user explicitly defers it, and it then goes under *Open questions*. Never fill a section with a
   plausible guess.

6. **Check whether this is several specs.** If it contains deliverables that can land
   independently and be useful on their own, propose splitting into consecutively numbered specs
   that name each other, and let the user decide. Mixed genres resolve here: "build it and
   document it" is two specs, not one document with extra sections. Do not split a sequence that
   only makes sense run end to end.

7. **Confirm.** Show the genre, the target path, and one line per section. For an update, show
   which sections change. Get agreement before writing.

8. **Write** the file from `templates/<genre>-spec.md`, creating directories as needed. Fill or
   remove every placeholder. When changing an existing spec, show what changes instead of
   replacing it silently.

9. **Report the genre and path, and stop.** Say that carrying the spec out is a separate step. Do
   not write code, prose, tests, or configuration, do not run the research, and do not create
   branches, commits, or issues.
