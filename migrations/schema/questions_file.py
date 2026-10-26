"""Load and validate the YAML question files in `migrations/`.

Each file holds one topic:

    topic: Kubernetes
    questions:
      - id: k8s-pod-lifecycle
        tags: [pods, basics]
        question: ...
        answer: ...
        explanation: ...
        active: true   # optional, default true
"""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import ValidationError

from .questions import Question, QuestionEntry
from .shared.models import Model, NonEmptyStr


class QuestionFile(Model):
    topic: NonEmptyStr
    questions: list[QuestionEntry]


@dataclass(frozen=True)
class DataError:
    """A problem in a YAML question file."""

    file: Path
    message: str
    question: str | None = None
    field: str | None = None

    def __str__(self) -> str:
        parts = [str(self.file)]
        if self.question is not None:
            parts.append(f"question {self.question}")
        if self.field is not None:
            parts.append(f"field {self.field}")
        return ": ".join([*parts, self.message])


def find_question_files(root: Path) -> list[Path]:
    """Every `*.yaml` file under `root`, except those inside `root/schema`."""
    schema = root / "schema"
    return sorted(path for path in root.rglob("*.yaml") if not path.is_relative_to(schema))


@dataclass(frozen=True)
class LoadedFile:
    questions: list[Question]
    """The questions that passed validation."""
    ids: list[str]
    """The id of every question entry that has a string id, valid or not."""
    errors: list[DataError]


def load_file(path: Path, name: Path | None = None) -> LoadedFile:
    """Load one question file. `name` is how errors refer to the file (default: `path`)."""
    name = name or path
    try:
        data = yaml.safe_load(path.read_text())
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        return LoadedFile([], [], [DataError(name, f"cannot read YAML: {error}")])
    if not isinstance(data, dict):
        message = "must be a mapping with the keys topic and questions"
        return LoadedFile([], [], [DataError(name, message)])
    try:
        QuestionFile.model_validate(data)
    except ValidationError as error:
        errors = list(_errors(name, data, error))
    else:
        errors = []
    entries = data.get("questions")
    if not isinstance(entries, list):
        return LoadedFile([], [], errors)
    questions, ids = [], []
    for entry in entries:
        if isinstance(entry_id := _entry_id(entry), str):
            ids.append(entry_id)
        try:
            questions.append(Question.model_validate({**entry, "topic": data.get("topic")}))
        except (TypeError, ValidationError):
            pass  # reported by the file validation above
    return LoadedFile(questions, ids, errors)


def _entry_id(entry: object) -> object:
    return entry.get("id") if isinstance(entry, dict) else None


def _errors(name: Path, data: dict, error: ValidationError) -> Iterator[DataError]:
    for detail in error.errors():
        loc = detail["loc"]
        if loc[0] != "questions" or len(loc) < 2:
            yield DataError(name, detail["msg"], field=".".join(map(str, loc)))
            continue
        index = loc[1]
        entry_id = _entry_id(data["questions"][index])
        question = entry_id if isinstance(entry_id, str) and entry_id else f"#{index}"
        field = ".".join(map(str, loc[2:])) or None
        yield DataError(name, detail["msg"], question=question, field=field)


def load_directory(root: Path) -> tuple[list[Question], list[DataError]]:
    """Load every question file under `root` and collect all errors, including duplicate ids."""
    questions, errors = [], []
    first_seen: dict[str, Path] = {}
    for path in find_question_files(root):
        name = path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path
        loaded = load_file(path, name)
        questions.extend(loaded.questions)
        errors.extend(loaded.errors)
        for question_id in loaded.ids:
            if question_id not in first_seen:
                first_seen[question_id] = name
                continue
            message = f"duplicate id, already used in {first_seen[question_id]}"
            errors.append(DataError(name, message, question=question_id, field="id"))
    return questions, errors
