# define-spec reference

## Classifying the genre

The deliverable decides the genre, not the topic. Ask what exists at the end that did not exist
before:

| What exists at the end | Genre |
| --- | --- |
| Working software | code |
| Prose someone reads | documentation |
| An answer that is not known yet | research |
| An agent skill | skill |
| A changed running system | operations |

Subjects that read both ways, where asking is required rather than optional:

- "spec the migration guide" - documentation (a guide) or operations (a migration)?
- "spec the changelog script" - code (a script) or skill (an agent skill)?
- "spec the evaluation of the new renderer" - research (decide whether) or code (build it)?
- "spec the API docs generator" - code (the generator) or documentation (the docs)?
- "spec the upgrade to version 3" - code (adapting to it) or operations (rolling it out)?

Rules:

- State the chosen genre to the user before the first interview round, always, even when it is
  obvious. A wrong pick found after the interview means the wrong questions were already asked.
- A subject that fits no genre gets code, and the fallback is stated out loud.
- Never invent a sixth genre, and never merge two genres into one document. A request that spans
  genres is a split - see the split test below.
- On an update, the existing spec's genre is kept unless the subject itself changed.

## Resolving the repository's conventions

Defaults are a fallback. Anything the repository states about specs wins, in this order:

1. An explicit instruction from the user in the current conversation.
2. The repository's agent instruction files, at the root and in the directory being worked in.
3. Contributing or development docs, and any README inside an existing spec directory.
4. The shape of the specs already there: their directory, filename, numbering style, and the
   section headings they share. Match them, including zero padding and filename, even when no
   document states the rule. A repository that prescribes its own section set for a kind of spec
   overrides the genre template too.
5. The defaults below.

Defaults: `docs/specs/<n>-<kebab-name>/task.md`, relative to the repository root.

State which convention was used when reporting the written path, so a wrong guess is visible.

## Numbering

- Plain integers starting at `1`, unless the existing specs are zero padded - then match their
  width.
- The next number is the highest existing number plus one. Do not reuse gaps, and do not renumber
  existing specs.
- When several specs are created from one interview, number them in the order they would be worked
  on.
- If two specs already share a number, ask rather than picking one.

## Naming

- Kebab-case, verb-first, ideally two to four words: `add-audit-log`, `migrate-session-store`,
  `compare-queue-backends`, `rewrite-getting-started`.
- Name the change, not the component (`add-retry-to-importer`, not `importer`).
- Nouns are acceptable when the deliverable is a thing rather than an action.

## Interview question banks

Ask in batches, skipping what the user has already answered. Use their vocabulary. The shared
block applies to every genre; then add the genre block.

### Shared

- What happens today that should not, or what cannot be done at all?
- Who notices, and when? What triggered bringing this up now?
- Which parts are in this piece of work, and what nearby must it *not* touch?
- Is there anything a reader would assume is included that is not?
- What must this run on, and what must already exist, be installed, or be accessible?
- Would any part of this be useful on its own, shipped before the rest?

### code

- What is true once this is done? How would you show someone it worked?
- Walk me through it step by step, in the order it happens.
- What are the inputs, and where do they come from?
- What should happen when it fails, or when input is empty, malformed, or huge?
- Is anything user-visible: output, messages, states, migrations?
- What has to be demonstrably true before you would call this done?
- What would make you reject the result even if it ran?
- For a bug: what are the exact steps to reproduce, what did you expect, what happened instead?

### documentation

- Who reads this, and what do they already know when they arrive?
- What can they do afterwards that they cannot do now?
- Where does each fact come from - which code, which existing document, which person?
- Is there anything currently documented that is now wrong and has to go?
- Which pages are written or changed, and where do they sit in the existing structure?
- What is the heading skeleton of each page?
- Are there code samples, and does anything check that they still run?
- Who reviews it, and what would make them reject it?

### research

- What exactly do you want answered? Phrase it as a question.
- How would you recognize a good answer when you see one?
- What decision does this feed, and who makes it?
- What happens if the answer comes out the way you do not expect?
- Which options or systems are worth examining, and which are already ruled out and why?
- What counts as evidence here - measurements, documentation, a prototype, an interview?
- May throwaway code be written? May anything be run against production data?
- What is produced at the end, and for whom?
- When is this over even if the answer is unsatisfying - which questions must be answered, or how
  much effort is it worth?

### skill

- What words would you actually type when you want this? Give me three phrasings.
- What is a request that sounds similar but must *not* set it off?
- Once it has fired, what should it refuse to do anyway?
- What does it do, step by step, and where does it stop?
- What does it need to know that is not in the request - files, conventions, context?
- Does any part of this get asked for on its own, at a different moment?
- Are there tools, an operating system, or a network connection it assumes?
- Does this repository already state rules for writing skills?

### operations

- What is the state now, and what is the state afterwards?
- In what order does this happen, and what is the rollback for each step?
- Is there a point after which rolling back is impossible or expensive? Where?
- Who breaks if this goes wrong, and how do they notice?
- Is there downtime or degradation, how long, and is it announced?
- What data is at risk, and where is the backup?
- Is this coordinated with anyone, and does it need a window?
- How do you confirm in the real environment that it worked - which numbers, over what period?
- When can the old path be deleted, and who tracks that?

## The split test

Split when a part has its own deliverable that is useful without the rest, or when parts would be
requested at different moments. Keep together when the steps only make sense as one uninterrupted
sequence and a half-finished state is not useful. Size is not the criterion.

A request that spans genres is almost always a split: "build it and document it" is a code spec
and a documentation spec, "evaluate the options and migrate" is a research spec and an operations
spec. Do not widen one document to cover both.

When splitting, each spec gets its own number, directory, and genre, and names the others by their
directory name.

## Updating an existing spec

- Amend the sections the new information touches, in place. Keep the number, directory, filename,
  and genre.
- Removed or reversed decisions get deleted or corrected, not appended as a history. The spec
  describes the intended end state; version control holds the history.
- Resolved open questions move into the section they belong to and leave *Open questions*.
- If the request adds an independently useful deliverable rather than clarifying this one, it is a
  new spec - propose that instead of growing this one.
- If the update changes what kind of thing is being produced, re-classify, say so, and rewrite the
  document from the new genre's template.

## Before writing

Shared:

- Every required section of the genre is answered from something the user said, not inferred.
- No placeholder text from the template remains.
- Non-goals name at least the assumptions a reader would otherwise make.
- The title, directory name, and subject are the same thing.
- Nothing in the document instructs anyone to carry the work out now.

Per genre:

- **code** - behavior covers the failure cases that came up, not only the happy path; every
  acceptance criterion maps to something in behavior or goal.
- **documentation** - every claim the outline promises has a named source; acceptance criteria are
  checkable without the author present.
- **research** - the stopping condition does not name the expected answer; every question is
  answerable, and answering all of them satisfies the stopping condition; the non-goals say that
  the winner is not implemented here.
- **skill** - anti-triggers and non-goals are not the same sentences reworded; the draft
  description contains the trigger phrasings and the main exclusions; acceptance criteria name
  three real phrasings and one adjacent request; no bundled file other than `SKILL.md` itself is
  named `SKILL.md` in any capitalization, at any depth, since installers match that basename and
  case-insensitive filesystems make a `skill.md` collide with it.
- **operations** - every step has a rollback or is explicitly marked as the point of no return;
  verification happens in the real environment, not in tests.
