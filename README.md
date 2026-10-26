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
in <TODO>

### Managing data via migration

You can also use migrations for managing your data. This is especially useful,
if you want to use git as you single source of truth.

<TODO>
