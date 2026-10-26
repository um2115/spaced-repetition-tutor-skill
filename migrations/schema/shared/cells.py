"""Convert Python values to Google Sheets cell strings and back.

Every parser raises ValueError with a short message when a cell cannot be read.
"""

from collections.abc import Iterable
from datetime import UTC, datetime


def format_str(value: str) -> str:
    return value


def parse_str(cell: str) -> str:
    return cell


def format_int(value: int | None) -> str:
    return "" if value is None else str(value)


def parse_int(cell: str) -> int:
    try:
        return int(cell.strip())
    except ValueError:
        raise ValueError(f"not an integer: {cell!r}") from None


def parse_optional_int(cell: str) -> int | None:
    return None if cell.strip() == "" else parse_int(cell)


def format_float(value: float | None) -> str:
    return "" if value is None else repr(float(value))


def parse_float(cell: str) -> float:
    try:
        return float(cell.strip())
    except ValueError:
        raise ValueError(f"not a number: {cell!r}") from None


def parse_optional_float(cell: str) -> float | None:
    return None if cell.strip() == "" else parse_float(cell)


def format_bool(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def parse_bool(cell: str) -> bool:
    match cell.strip().upper():
        case "TRUE":
            return True
        case "FALSE":
            return False
    raise ValueError(f"not TRUE or FALSE: {cell!r}")


def format_list(values: Iterable) -> str:
    return ",".join(str(value) for value in values)


def parse_list(cell: str) -> list[str]:
    if cell.strip() == "":
        return []
    return [item.strip() for item in cell.split(",")]


def parse_float_list(cell: str) -> list[float]:
    return [parse_float(item) for item in parse_list(cell)]


def format_float_list(values: list[float]) -> str:
    return format_list(format_float(value) for value in values)


def format_timestamp(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_timestamp(cell: str) -> datetime:
    try:
        value = datetime.fromisoformat(cell.strip())
    except ValueError:
        raise ValueError(f"not an ISO 8601 timestamp: {cell!r}") from None
    if value.tzinfo is None:
        raise ValueError(f"timestamp has no time zone: {cell!r}")
    return value.astimezone(UTC)


def parse_optional_timestamp(cell: str) -> datetime | None:
    return None if cell.strip() == "" else parse_timestamp(cell)
