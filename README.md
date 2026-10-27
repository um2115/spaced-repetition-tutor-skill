# Spaced repetition tutor skill

A workspace for creating a skill that should help you with questions optimized
for spaced repetition.

## The concept

### Spaced repetition

Spaced repetition is a learning technique which shows you a question you must
answer. Newer or harder questions are shown more frequently in comparison to
older or easier ones. The difficulty of the questions is often determined by
the rate of false answers. This helps to learn more effectively.

(See the wiki for that https://en.wikipedia.org/wiki/Spaced_repetition)

### AI tutor

The ai should ask you the question and judge if the answer is correct. If the
answer is wrong, the ai tutor can help to close the gaps in your understanding
by explaining you the topic again and answering questions.

## How to setup

<TO DO> SETUP TASKS

## Use the skill

<TO DO>

## Data

The data is hold in a google sheets document. Agents can access those via
different MCP servers. The data can be managed in two ways:

1. Manually by hand
2. Programmatically using migrations

### Managing data manually by hand

You can simply write/update the document by hand or let the agent do it.
The only constraint is that each entry must be compliant to the schema defined
in [the data schema](docs/data-schema.md).

### Managing data via migration

You can also use migrations for managing your data. This is especially useful,
if you want to use git as you single source of truth.

#### One-time setup

You need [mise](https://mise.jdx.dev), which installs Python and uv for you
(`mise install`), and access to the Google Sheet:

1. In the [Google Cloud console](https://console.cloud.google.com), create a
   project (or pick one) and enable the **Google Sheets API**.
2. Configure the OAuth consent screen and add your Google account as a test
   user.
3. Create an OAuth client ID of type **Desktop app** and download its JSON file,
   the client secret.
4. Tell the scripts where everything is by filling in the variables in
   `mise.local.toml` (ignored by git; create it with an `[env]` section if it is
   missing):

   ```toml
   [env]
   SRT_SHEET_ID = "1AbC...xyz"   # the id from the sheet URL: docs.google.com/spreadsheets/d/<id>/edit
   SRT_OAUTH_CLIENT_SECRET = "{{env.HOME}}/.config/srt/client_secret.json"
   SRT_OAUTH_TOKEN = "{{env.HOME}}/.config/srt/token.json"   # created on the first login
   ```

   mise does not expand `~`, so use absolute paths or `{{env.HOME}}`. The
   values in `mise.local.toml` override variables exported in your shell, even
   when they are empty. Instead of the variables you can pass `--sheet-id`,
   `--client-secret` and `--token` to each command. Keep both files out of the
   repository.

The first command that talks to the sheet opens your browser for the Google
login and stores the token at `SRT_OAUTH_TOKEN`. Later runs reuse it.

#### Write questions

Put your questions in YAML files in `migrations/questions/`, one topic per
file:

```yaml
topic: Git
questions:
  - id: git-rebase
    tags: [branches]
    question: What does git rebase do?
    answer: It replays commits onto another base.
    explanation: Rebasing rewrites the commits of a branch on top of another commit.
```

[The data schema](docs/data-schema.md) describes every field. Check the files
with:

```sh
mise run check:data
```

#### Migrate the sheet

```sh
mise run migrate            # show what would change, write nothing
mise run migrate --apply    # write the changes
```

The sheet can be new and empty: the first `--apply` creates all tabs with their
header rows. After that, each run brings the sheet to the latest schema version
and writes your YAML questions into the `questions` tab. It prints what it did:

- new questions are appended,
- questions whose sheet row differs from the YAML are overwritten,
- questions you removed from YAML stay in the sheet and are only reported (set
  `active: false` to retire one),
- questions you added by hand in the sheet are left alone and reported.

Edit the questions that come from YAML in the YAML, not in the sheet: the next
run overwrites hand edits of those rows.

#### Restore a snapshot

Before a migration step changes the structure of the sheet, `migrate --apply`
saves a copy of the whole sheet to `snapshots/<timestamp>/` and prints the
path. If something went wrong, write it back:

```sh
mise run restore snapshots/20261026T143005Z           # show what would be written
mise run restore snapshots/20261026T143005Z --apply   # write it back
```

Restoring replaces every tab in the snapshot. Reviews the tutor recorded after
the snapshot was taken are lost.
