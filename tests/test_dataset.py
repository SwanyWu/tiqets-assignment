"""The bundled exports: ranking, unused stock, and the rows that are left out."""

from pathlib import Path

from tiqets.models import IssueCode
from tiqets.process import generate

ROOT = Path(__file__).resolve().parents[1]
DUPLICATE_BARCODES = {
    "11111111595",
    "11111111649",
    "11111111665",
    "11111111674",
    "11111111700",
}
EMPTY_ORDERS = {"75", "108", "201"}


def test_bundled_exports_match_the_known_report() -> None:
    report = generate(ROOT / "data" / "orders.csv", ROOT / "data" / "barcodes.csv")

    assert report.top_customers == (
        ("10", 23),
        ("56", 20),
        ("29", 16),
        ("60", 16),
        ("59", 15),
    )
    assert report.unused_barcodes == 98
    assert len(report.lines) == 204

    order_ids = [line.order_id for line in report.lines]
    assert EMPTY_ORDERS.isdisjoint(order_ids)
    printed = {barcode for line in report.lines for barcode in line.barcodes}
    assert DUPLICATE_BARCODES.isdisjoint(printed)

    duplicate_issues = [
        issue for issue in report.issues if issue.code is IssueCode.DUPLICATE_BARCODE
    ]
    empty_issues = [
        issue for issue in report.issues if issue.code is IssueCode.ORDER_WITHOUT_BARCODES
    ]
    assert len(duplicate_issues) == 5
    assert {issue.message.split()[1] for issue in empty_issues} == EMPTY_ORDERS


def test_bundled_lines_are_sorted_as_text() -> None:
    report = generate(ROOT / "data" / "orders.csv", ROOT / "data" / "barcodes.csv")
    keys = [(line.customer_id, line.order_id) for line in report.lines]

    assert keys == sorted(keys)
    customer_10 = [order_id for customer_id, order_id in keys if customer_id == "10"]
    assert customer_10.index("139") < customer_10.index("18")
