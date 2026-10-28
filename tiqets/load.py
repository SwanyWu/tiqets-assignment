"""Read the order and barcode CSV exports."""

import csv
from pathlib import Path

from tiqets.models import BarcodeRecord, Issue, OrderRecord, ReadResult

ORDER_COLUMNS = ("order_id", "customer_id")
BARCODE_COLUMNS = ("barcode", "order_id")

class InputError(Exception):
    """An export cannot be read, or its header is not the expected one."""


def load_orders(path: Path) -> ReadResult[OrderRecord]:
    records: list[OrderRecord] = []
    issues: list[Issue] = []
    for row in _read_rows(path, ORDER_COLUMNS):
        parsed = _parse_order(row)
        if isinstance(parsed, Issue):
            issues.append(parsed)
        else:
            records.append(parsed)
    return ReadResult(tuple(records), tuple(issues))


def load_barcodes(path: Path) -> ReadResult[BarcodeRecord]:
    records: list[BarcodeRecord] = []
    issues: list[Issue] = []
    for row in _read_rows(path, BARCODE_COLUMNS):
        parsed = _parse_barcode(row)
        if isinstance(parsed, Issue):
            issues.append(parsed)
        else:
            records.append(parsed)
    return ReadResult(tuple(records), tuple(issues))


def normalize_id(value: str) -> str:
    if value.isdigit():
        return str(int(value))
    return value


def _read_rows(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration:
                raise InputError(f"{path} is empty or has no header") from None
            fieldnames = _header(path, header, required)
            rows: list[dict[str, str]] = []
            width = len(fieldnames)
            for raw in reader:
                if not raw or all(cell.strip() == "" for cell in raw):
                    continue
                cells = [cell.strip() for cell in raw]
                if len(cells) < width:
                    cells.extend([""] * (width - len(cells)))
                rows.append(dict(zip(fieldnames, cells, strict=False)))
            return rows
    except FileNotFoundError as exc:
        raise InputError(f"file not found: {path}") from exc
    except IsADirectoryError as exc:
        raise InputError(f"path is a directory: {path}") from exc
    except UnicodeDecodeError as exc:
        raise InputError(f"{path} is not valid UTF-8") from exc
    except csv.Error as exc:
        raise InputError(f"{path} is not valid CSV: {exc}") from exc


def _header(path: Path, header: list[str], required: tuple[str, ...]) -> list[str]:
    fieldnames = [name.strip().lower() for name in header]
    if fieldnames and fieldnames[-1] == "":
        fieldnames = fieldnames[:-1]
    if not fieldnames:
        raise InputError(f"{path} is empty or has no header")
    if any(name == "" for name in fieldnames):
        raise InputError(f"{path} has a blank column name")
    duplicates = sorted({name for name in fieldnames if fieldnames.count(name) > 1})
    if duplicates:
        raise InputError(f"{path} has duplicate columns: {', '.join(duplicates)}")
    missing = [column for column in required if column not in fieldnames]
    if missing:
        found = ", ".join(fieldnames)
        raise InputError(
            f"{path} is missing column(s): {', '.join(missing)}. Found: {found}"
        )
    return fieldnames


def _parse_order(row: dict[str, str]) -> OrderRecord | Issue:
    order_id = row.get("order_id", "").strip()
    customer_id = row.get("customer_id", "").strip()
    return OrderRecord(normalize_id(order_id), normalize_id(customer_id))


def _parse_barcode(row: dict[str, str]) -> BarcodeRecord | Issue:
    barcode = row.get("barcode", "").strip()
    order_id = row.get("order_id", "").strip()
    if order_id == "":
        return BarcodeRecord(barcode, None)
    return BarcodeRecord(barcode, normalize_id(order_id))
