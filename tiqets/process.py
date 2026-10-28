"""Join orders to barcodes and apply the voucher validation rules."""

from collections import Counter, defaultdict
from pathlib import Path

from tiqets.load import load_barcodes, load_orders
from tiqets.models import BarcodeRecord, Issue, IssueCode, OrderRecord, Report, VoucherLine


def generate(orders_path: Path, barcodes_path: Path, top: int = 5) -> Report:
    """Load both exports and return the voucher report.

    Args:
        orders_path: CSV with order_id and customer_id.
        barcodes_path: CSV with barcode and order_id.
        top: How many customers to rank. Must be at least 1.

    Returns:
        Voucher lines, the top customers, the unused-barcode count, and every
        issue from loading the files or building the report.

    Example:
        generate(Path("data/input/orders.csv"), Path("data/input/barcodes.csv"))
        writes nothing. The caller prints the report and writes the file.
    """
    orders = load_orders(orders_path)
    barcodes = load_barcodes(barcodes_path)
    report = build_report(orders.records, barcodes.records, top=top)
    return Report(
        lines=report.lines,
        top_customers=report.top_customers,
        unused_barcodes=report.unused_barcodes,
        issues=orders.issues + barcodes.issues + report.issues,
    )


def build_report(
    orders: tuple[OrderRecord, ...] | list[OrderRecord],
    barcodes: tuple[BarcodeRecord, ...] | list[BarcodeRecord],
    top: int = 5,
) -> Report:
    """Join orders to barcodes and apply the voucher rules.

    Args:
        orders: Order rows already read from the export.
        barcodes: Barcode rows already read from the export.
        top: How many customers to rank. Must be at least 1.

    Returns:
        Voucher lines sorted by customer id then order id, the top customers,
        the unused-barcode count, and the rows that were skipped. A repeated
        barcode is dropped entirely. An order with no barcodes is left out.

    Raises:
        ValueError: top is less than 1.

    Example:
        One order (1, customer 10) and barcodes "222" and "111" on that order
        produce a line VoucherLine("10", "1", ("111", "222")).
    """
    if top < 1:
        raise ValueError("top must be at least 1")

    unique_barcodes, issues = _unique_barcodes(barcodes)
    orders_by_id: dict[str, OrderRecord] = {
        record.order_id: record for record in orders
    }
    assigned, unused = _assign_barcode_to_order(unique_barcodes, orders_by_id)
    lines = _voucher_lines(orders, assigned, issues)
    return Report(
        lines=tuple(lines),
        top_customers=_top_customers(lines, top),
        unused_barcodes=unused,
        issues=tuple(issues),
    )


def _unique_barcodes(
    barcodes: tuple[BarcodeRecord, ...] | list[BarcodeRecord],
) -> tuple[list[BarcodeRecord], list[Issue]]:
    counts = Counter(record.barcode for record in barcodes)
    issues: list[Issue] = []
    for barcode, count in counts.items():
        if count == 1:
            continue
        issues.append(
            Issue(
                IssueCode.DUPLICATE_BARCODE,
                f"duplicate barcode {barcode}; ignoring every occurrence",
            )
        )
    unique = [record for record in barcodes if counts[record.barcode] == 1]
    return unique, issues


def _assign_barcode_to_order(
    barcodes: list[BarcodeRecord],
    orders_by_id: dict[str, OrderRecord],
) -> tuple[dict[str, list[str]], int]:
    """Group sold barcodes by order id and count the unsold ones.

    Args:
        barcodes: Barcode rows that survived the duplicate check.
        orders_by_id: Orders keyed by order id.

    Returns:
        Barcodes grouped by order id, and how many barcodes have a blank order id.
        A barcode whose order is missing is left out of both.

    Example:
        ({"1": ["111", "222"]}, 1) is order 1 with those barcodes, plus one unsold.
    """
    assigned: dict[str, list[str]] = defaultdict(list)
    unused = 0
    for record in barcodes:
        if record.order_id is None:
            unused += 1
            continue
        if record.order_id in orders_by_id:
            assigned[record.order_id].append(record.barcode)
    return assigned, unused


def _voucher_lines(
    orders: tuple[OrderRecord, ...] | list[OrderRecord],
    assigned: dict[str, list[str]],
    issues: list[Issue],
) -> list[VoucherLine]:
    """Build one voucher line per order that has barcodes.

    Args:
        orders: Order rows, in file order.
        assigned: Barcodes already grouped by order id.
        issues: Collects an order that has no barcodes.

    Returns:
        Lines sorted by customer id, then order id.

    Example:
        Orders (1, customer 10) and (2, customer 11), with
        {"1": ["222", "111"]} assigned, produce
        [VoucherLine("10", "1", ("111", "222"))]. Order 2 is an issue.
    """
    lines: list[VoucherLine] = []
    for record in orders:
        barcodes = assigned.get(record.order_id, [])
        if not barcodes:
            issues.append(
                Issue(
                    IssueCode.ORDER_WITHOUT_BARCODES,
                    (
                        f"order {record.order_id} for customer {record.customer_id} "
                        "has no barcodes; ignoring"
                    ),
                )
            )
            continue
        lines.append(
            VoucherLine(
                customer_id=record.customer_id,
                order_id=record.order_id,
                barcodes=tuple(sorted(barcodes)),
            )
        )
    lines.sort(key=lambda line: (line.customer_id, line.order_id))
    return lines


def _top_customers(lines: list[VoucherLine], top: int) -> tuple[tuple[str, int], ...]:
    counts: dict[str, int] = defaultdict(int)
    for line in lines:
        counts[line.customer_id] += len(line.barcodes)
    ranked = sorted(
        counts,
        key=lambda customer_id: (-counts[customer_id], customer_id),
    )
    return tuple((customer_id, counts[customer_id]) for customer_id in ranked[:top])
