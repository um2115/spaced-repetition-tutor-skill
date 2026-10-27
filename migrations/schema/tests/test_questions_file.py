import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from migrations.schema.check import QUESTIONS, main
from migrations.schema.questions_file import load_directory, load_directory_with_files

ROOT = Path(__file__).resolve().parents[3]

KUBERNETES = """\
    topic: Kubernetes
    questions:
      - id: k8s-pod-lifecycle
        tags: [pods, basics]
        question: Which phases can a pod be in?
        answer: Pending, Running, Succeeded, Failed, Unknown
        explanation: The phase is a high-level summary of where the pod is in its lifecycle.
      - id: k8s-service-types
        question: Name the Service types.
        answer: ClusterIP, NodePort, LoadBalancer, ExternalName
        explanation: The type decides how the Service is exposed.
        active: false
"""

PYTHON = """\
    topic: Python
    questions:
      - id: py-gil
        tags: []
        question: What does the GIL do?
        answer: It lets only one thread run Python bytecode at a time.
        explanation: The global interpreter lock protects the interpreter's internal state.
"""


def write(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text))
    return path


def entry(**fields) -> str:
    """A one-question topic file built from the given question fields."""
    base = {
        "id": "a-question",
        "question": "Q?",
        "answer": "A.",
        "explanation": "Because.",
    }
    base.update(fields)
    lines = ["topic: Test", "questions:"]
    for i, (key, value) in enumerate((k, v) for k, v in base.items() if v is not None):
        lines.append(f"  {'- ' if i == 0 else '  '}{key}: {value}")
    return "\n".join(lines) + "\n"


@pytest.fixture
def migrations(tmp_path: Path) -> Path:
    return tmp_path / "migrations"


def test_valid_files_load(migrations: Path):
    write(migrations, "kubernetes.yaml", KUBERNETES)
    write(migrations, "nested/python.yaml", PYTHON)

    questions, errors = load_directory(migrations)

    assert errors == []
    by_id = {question.id: question for question in questions}
    assert set(by_id) == {"k8s-pod-lifecycle", "k8s-service-types", "py-gil"}
    assert by_id["k8s-pod-lifecycle"].topic == "Kubernetes"
    assert by_id["k8s-pod-lifecycle"].tags == ["pods", "basics"]
    assert by_id["k8s-pod-lifecycle"].active is True
    assert by_id["k8s-service-types"].active is False
    assert by_id["py-gil"].topic == "Python"


def test_check_passes_on_valid_files(migrations: Path, capsys):
    write(migrations, "kubernetes.yaml", KUBERNETES)
    write(migrations, "python.yaml", PYTHON)

    assert main([str(migrations)]) == 0
    assert "3 question(s) valid" in capsys.readouterr().out


def test_empty_directory_is_valid(migrations: Path):
    migrations.mkdir()
    assert main([str(migrations)]) == 0


def test_default_directory_is_migrations_questions():
    assert QUESTIONS == ROOT / "migrations" / "questions"


def test_files_are_paired_with_their_path(migrations: Path):
    kubernetes = write(migrations, "kubernetes.yaml", KUBERNETES)
    python = write(migrations, "nested/python.yaml", PYTHON)

    sourced, errors = load_directory_with_files(migrations)

    assert errors == []
    assert {question.id: path for question, path in sourced} == {
        "k8s-pod-lifecycle": kubernetes,
        "k8s-service-types": kubernetes,
        "py-gil": python,
    }


@pytest.mark.parametrize(
    ("text", "question", "field", "message"),
    [
        (entry(id="Bad-Id"), "Bad-Id", "id", "should match pattern"),
        (entry(id="'bad id'"), "bad id", "id", "should match pattern"),
        (entry(answer=None), "a-question", "answer", "Field required"),
        (entry(explanation="''"), "a-question", "explanation", "must not be empty"),
        (entry(explanation="'   '"), "a-question", "explanation", "must not be empty"),
        (entry(hint="extra"), "a-question", "hint", "Extra inputs are not permitted"),
        (entry(active='"yes"'), "a-question", "active", "valid boolean"),
        (entry(answer=42), "a-question", "answer", "valid string"),
        (entry(tags="pods"), "a-question", "tags", "valid list"),
        (entry(tags="['a,b']"), "a-question", "tags.0", "without commas"),
        (entry(topic="Other"), "a-question", "topic", "Extra inputs are not permitted"),
    ],
)
def test_invalid_question(migrations, capsys, text, question, field, message):
    path = write(migrations, "test.yaml", text)

    _, errors = load_directory(migrations)

    assert len(errors) == 1
    error = errors[0]
    assert (error.file.name, error.question, error.field) == (path.name, question, field)
    assert message in error.message
    assert main([str(migrations)]) == 1
    output = capsys.readouterr().err
    assert f"test.yaml: question {question}: field {field}: " in output


def test_question_without_id_is_named_by_index(migrations: Path):
    write(migrations, "test.yaml", entry(id=None))

    _, errors = load_directory(migrations)

    assert [(e.question, e.field) for e in errors] == [("#0", "id")]


@pytest.mark.parametrize(
    ("text", "field"),
    [
        ("questions: []\n", "topic"),
        ("topic: Test\n", "questions"),
        ("topic: ''\nquestions: []\n", "topic"),
    ],
)
def test_file_without_topic_or_questions(migrations: Path, text: str, field: str):
    write(migrations, "test.yaml", text)

    _, errors = load_directory(migrations)

    assert [(e.question, e.field) for e in errors] == [(None, field)]


@pytest.mark.parametrize("text", ["", "- a list\n", "topic: [unclosed\n"])
def test_file_that_is_not_a_mapping(migrations: Path, text: str):
    write(migrations, "test.yaml", text)

    _, errors = load_directory(migrations)

    assert len(errors) == 1
    assert errors[0].file.name == "test.yaml"


def test_duplicate_id_across_files(migrations: Path):
    write(migrations, "a.yaml", KUBERNETES)
    write(migrations, "b.yaml", entry(id="k8s-pod-lifecycle"))

    _, errors = load_directory(migrations)

    assert [(e.file.name, e.question, e.field) for e in errors] == [
        ("b.yaml", "k8s-pod-lifecycle", "id")
    ]
    assert "a.yaml" in errors[0].message


def test_duplicate_id_found_next_to_other_errors(migrations: Path):
    write(migrations, "a.yaml", KUBERNETES)
    text = entry(id="k8s-pod-lifecycle") + "  - id: broken\n"
    write(migrations, "b.yaml", text)

    _, errors = load_directory(migrations)

    assert {(e.question, e.field) for e in errors} == {
        ("k8s-pod-lifecycle", "id"),
        ("broken", "question"),
        ("broken", "answer"),
        ("broken", "explanation"),
    }


def test_all_errors_of_several_files_are_reported(migrations: Path, capsys):
    write(migrations, "kubernetes.yaml", KUBERNETES)
    write(migrations, "one.yaml", entry(id="Bad-Id", answer=None))
    write(migrations, "two.yaml", entry(id="k8s-pod-lifecycle", active='"yes"'))
    write(migrations, "three.yaml", "questions: []\n")

    assert main([str(migrations)]) == 1

    output = capsys.readouterr().err
    assert "one.yaml: question Bad-Id: field id: " in output
    assert "one.yaml: question Bad-Id: field answer: " in output
    assert "two.yaml: question k8s-pod-lifecycle: field active: " in output
    assert "two.yaml: question k8s-pod-lifecycle: field id: duplicate id" in output
    assert "three.yaml: field topic: " in output
    assert "5 error(s)" in output


def test_check_runs_as_module(migrations: Path):
    write(migrations, "test.yaml", entry(id="Bad-Id"))

    result = subprocess.run(
        [sys.executable, "-m", "migrations.schema.check", str(migrations)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "question Bad-Id: field id: " in result.stderr
