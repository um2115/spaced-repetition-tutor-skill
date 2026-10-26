# Code structure

- Derive the module structure from the domain, not from technical layers. One module per domain
  concept holds everything about it: for example `migrations/schema/questions.py` holds the
  question models and the `questions` tab, not a `models.py` next to a `tabs.py`.
- Technical building blocks that several domain modules use live in a `shared/` package next to
  them (for example `migrations/schema/shared/`). A building block used by one domain module
  stays in that module.
- Tests mirror the module layout: `tests/test_<module>.py` for a domain module,
  `tests/shared/test_<module>.py` for a shared one.
- Explain non-obvious design choices in the docstring of the code they concern, such as why two
  similar models exist side by side.
