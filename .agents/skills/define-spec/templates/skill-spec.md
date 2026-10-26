# <n>-<kebab-name>

One sentence naming the skill and what it does.

## Problem

What goes wrong today without this skill, and in which situations.

## Goal

What the skill achieves when it fires, in one paragraph.

## Triggers

The phrasings, in the words a user would really type, that must activate the skill.

- "..."
- "..."
- "..."

## Anti-triggers

Adjacent requests that must not activate it. An anti-trigger is about activation; a non-goal is
about behavior once activated. Keep them apart.

- ...

## Behavior

Step by step, what the skill does when it fires, including what it asks and when it stops.

1. ...
2. ...

## Scope

### In scope

- What this skill covers.

### Out of scope (non-goals)

- What it will not do even though it activated - distinct from the anti-triggers above, which are
  requests it must not react to at all.

## Draft description

The description is the only text loaded before activation, so it is drafted here. Third person,
when-to-use, containing the trigger phrasings and the main exclusions.

> ...

## Constraints & assumptions

- Harness-agnostic: frontmatter carries only `name` and `description`, bundled files are
  referenced by relative path, no harness-specific tool, command, or agent is named.
- `SKILL.md` is reserved: no other file in the bundle, at any depth, is named `SKILL.md` in any
  capitalization. Installers match that basename several levels deep, and on case-insensitive
  filesystems a `skill.md` collides with it and breaks the install.
- Assumptions about operating system, installed command line tools, or network access.
- Where the repository states its own rules for authoring skills, those rules win over this
  template.

## Acceptance criteria

- [ ] Three phrasings a user would really type activate it: "...", "...", "...".
- [ ] The adjacent request "..." does not activate it.
- [ ] Read cold, with no other context, every step is executable without knowledge that is not in
      the skill or its referenced files.
- [ ] The skill does only what the behavior above states.

## Open questions

Only items the user explicitly deferred. Remove this section when there are none.

- ...
