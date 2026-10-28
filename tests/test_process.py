"""Join rules: duplicate barcodes, empty orders, unused stock, and ordering."""

import pytest

from tiqets.models import BarcodeRecord, IssueCode, OrderRecord
from tiqets.process import build_report, generate


def test_barcodes_on_a_line_are_sorted_and_unsold_stock_is_counted() -> None:
    report = build_report(
        [OrderRecord("1", "10")],
        [
            BarcodeRecord("b", "1"),
            BarcodeRecord("a", "1"),
            BarcodeRecord("stock", None),
        ],
    )

    assert report.lines[0].barcodes == ("a", "b")
    assert report.lines[0].render() == "10, 1, [a, b]"
    assert report.unused_barcodes == 1
    assert report.issues == ()


def test_every_copy_of_a_duplicate_barcode_is_dropped() -> None:
    report = build_report(
        [OrderRecord("1", "10")],
        [
            BarcodeRecord("dup", "1"),
            BarcodeRecord("dup", None),
            BarcodeRecord("sold", "1"),
            BarcodeRecord("stock", None),
        ],
    )

    assert report.lines[0].barcodes == ("sold",)
    assert report.unused_barcodes == 1
    assert report.issues[0].code is IssueCode.DUPLICATE_BARCODE
    assert "dup" in report.issues[0].message


def test_order_with_no_barcodes_is_omitted() -> None:
    report = build_report(
        [OrderRecord("1", "10"), OrderRecord("2", "11")],
        [BarcodeRecord("a", "1")],
    )

    assert [line.order_id for line in report.lines] == ["1"]
    assert report.issues[0].code is IssueCode.ORDER_WITHOUT_BARCODES
    assert "order 2 for customer 11" in report.issues[0].message


def test_barcode_for_an_unknown_order_is_not_stock() -> None:
    report = build_report(
        [OrderRecord("1", "10")],
        [BarcodeRecord("ghost", "999"), BarcodeRecord("stock", None)],
    )

    assert report.lines == ()
    assert report.unused_barcodes == 1
    assert report.issues[0].code is IssueCode.ORDER_WITHOUT_BARCODES


def test_repeated_order_id_is_printed_once_per_row() -> None:
    report = build_report(
        [OrderRecord("1", "10"), OrderRecord("1", "11")],
        [BarcodeRecord("aaa", "1")],
    )

    assert [(line.customer_id, line.order_id) for line in report.lines] == [
        ("10", "1"),
        ("11", "1"),
    ]


def test_tie_is_broken_by_customer_id_text() -> None:
    report = build_report(
        [OrderRecord("1", "60"), OrderRecord("2", "29")],
        [BarcodeRecord("a", "1"), BarcodeRecord("b", "2")],
    )

    assert report.top_customers == (("29", 1), ("60", 1))


def test_generate_reads_exports(tmp_path) -> None:
    orders = tmp_path / "orders.csv"
    barcodes = tmp_path / "barcodes.csv"
    orders.write_text("order_id,customer_id\n007,10\n", encoding="utf-8")
    barcodes.write_text("barcode,order_id\n111,007\n", encoding="utf-8")

    report = generate(orders, barcodes, top=1)

    assert report.lines[0].render() == "10, 007, [111]"
    assert report.top_customers == (("10", 1),)
    assert report.unused_barcodes == 0
