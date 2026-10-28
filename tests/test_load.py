"""CSV reading: headers, id text, and files that cannot be read."""

from pathlib import Path

import pytest

from tiqets.load import InputError, load_orders


def test_missing_column_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "orders.csv"
    path.write_text("order_id\n1\n", encoding="utf-8")

    with pytest.raises(InputError, match="missing column"):
        load_orders(path)


def test_duplicate_column_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "orders.csv"
    path.write_text("order_id,order_id,customer_id\n1,1,10\n", encoding="utf-8")

    with pytest.raises(InputError, match="duplicate columns"):
        load_orders(path)


def test_missing_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(InputError, match="file not found"):
        load_orders(tmp_path / "missing.csv")


def test_empty_file_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "orders.csv"
    path.write_text("", encoding="utf-8")

    with pytest.raises(InputError, match="no header"):
        load_orders(path)
