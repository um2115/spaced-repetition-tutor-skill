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

### What you need

- An AI agent that can **run code** (Python 3.10 or newer, nothing else to
  install) and has a **Google Sheets connection** (an MCP server or connector
  that can read and write sheets). Any agent with both works, for example
  Claude on claude.ai with code execution turned on.
- A Google Sheet for your questions and review history, set up as described in
  [the data schema](docs/data-schema.md). The quickest way is to let the
  migration create the tabs, see
  [Managing data via migration](#managing-data-via-migration). You can also
  create the tabs and header rows by hand.

### Install the skill

The skill is the folder `.agents/skills/spaced-repetition-tutor/` in this
repository. It already contains everything it needs: the instructions, the
scheduling script and a copy of the data schema.

- **claude.ai:** tell Claude that the GitHub repository at your link holds a
  skill called `spaced-repetition-tutor` in `.agents/skills/` and that it
  should install it. Claude then adds it to its skills.
- **Other agents:** copy or link the folder into the agent's skills directory.
  Claude Code finds it in this repository already, via
  `.claude/skills/spaced-repetition-tutor`.

After an update of the repository, install the skill again. Its version is in
`.agents/skills/spaced-repetition-tutor/VERSION`.

## Use the skill

### Start a session

The tutor never starts on its own. Call it by name, and tell it which sheet to
use if you have not shared one in the conversation yet:

```text
/spaced-repetition-tutor
start the spaced repetition tutor with https://docs.google.com/spreadsheets/d/<id>/edit
spaced repetition tutor, 10 questions tagged git
spaced repetition tutor, topic Kubernetes
```

- **Sheet:** a link, id or title. If you name none and the conversation has
  no sheet or several, the tutor asks which one to use.
- **Number of questions:** optional. Without one, the tutor goes on until no
  question is due.
- **Tags and topics:** optional. Only questions with one of the named tags, or
  of one of the named topics, are asked.

A plain "quiz me on git" does not start the tutor; the agent answers it like
any other request.

### During a session

1. The tutor asks the questions that are due, the most overdue first, then the
   questions you have never answered.
2. Answer in your own words. The tutor judges the meaning, not the wording, and
   rates your answer: **Again** (wrong), **Hard**, **Good** or **Easy**. It
   shows you the expected answer, the rating and why.
3. You can discuss the rating or ask about the answer. That helps you, but it
   does not change the rating.
4. On a wrong answer the tutor explains the topic until you say it is clear,
   and asks the question again later in the same session. These repeats do not
   count toward the number of questions you asked for.
5. You can stop at any time. Every answer is saved right after it is rated.

At the end the tutor shows a summary: how many questions you answered, their
ratings, and when the next question is due.

### What the tutor writes

The tutor only writes the `state` tab (when each question is due next) and
appends to the `log` tab (every answer you gave). It never changes your
questions or the `config` tab. The scheduling follows
[FSRS](https://github.com/open-spaced-repetition/py-fsrs): questions you answer
well come back after longer and longer intervals, questions you get wrong come
back soon. You can tune it in the `config` tab, see
[the data schema](docs/data-schema.md).

### When it stops

- **No code execution:** the tutor needs it to schedule reviews and stops.
- **Schema version mismatch:** the sheet's `schema_version` differs from the
  one the skill knows. Run the migration or install the current skill.
- **Invalid `config`:** the tutor names the problem; fix the `config` tab.
- **Nothing due:** come back later.

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
