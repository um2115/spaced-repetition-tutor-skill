# <n>-<kebab-name>

One sentence naming the migration, rollout, or infrastructure change.

## Problem

What the current setup costs or risks, and what forces the change now.

## Goal

The state of the running system once this is done.

## Scope

### In scope

- Which systems, environments, data, and pipelines are touched.

### Out of scope (non-goals)

- Neighbouring systems deliberately left alone, and cleanup deferred to later.

## Sequence & reversibility

Each step in the order it is carried out, with its rollback. Mark the point of no return
explicitly - the step after which rolling back is no longer possible or no longer cheap.

1. ... - rollback: ...
2. ... - rollback: ...
3. **Point of no return** - ... - after this, recovery means ...

## Blast radius

- Who or what breaks if this goes wrong, and how it shows up for them.
- Downtime or degradation window, and whether it is announced.
- Data at risk, and where the backup is.

## Constraints & assumptions

- Maintenance windows, access and credentials, quotas, versions, coordination with other teams,
  anything assumed about the environment.

## Verification

How success is confirmed in the real environment, not in tests.

- [ ] ... (e.g. zero rows lost, measured by ...)
- [ ] ... (e.g. p99 unchanged over ...)
- [ ] The old path can be removed after ..., and this is tracked.

## Open questions

Only items the user explicitly deferred. Remove this section when there are none.

- ...
