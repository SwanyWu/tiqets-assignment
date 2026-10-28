"""Join orders to barcodes and apply the voucher validation rules."""

from collections import defaultdict
from pathlib import Path

from tiqets.load import load_barcodes, load_orders
from tiqets.models import BarcodeRecord, Issue, IssueCode, OrderRecord, Report, VoucherLine


def generate(orders_path: Path, barcodes_path: Path, top: int = 5) -> Report:
    if top < 1:
        raise ValueError("top must be at least 1")
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
    if top < 1:
        raise ValueError("top must be at least 1")

    issues: list[Issue] = []
    unique_barcodes = _unique_barcodes(barcodes, issues)
    orders_by_id: dict[str, OrderRecord] = {
        record.order_id: record for record in orders
    }
    assigned, unused = _assign(unique_barcodes, orders_by_id)
    lines = _voucher_lines(orders, assigned, issues)
    return Report(
        lines=tuple(lines),
        top_customers=_top_customers(lines, top),
        unused_barcodes=unused,
        issues=tuple(issues),
    )


def _unique_barcodes(
    barcodes: tuple[BarcodeRecord, ...] | list[BarcodeRecord],
    issues: list[Issue],
) -> list[BarcodeRecord]:
    grouped: dict[str, list[BarcodeRecord]] = defaultdict(list)
    for record in barcodes:
        grouped[record.barcode].append(record)

    unique: list[BarcodeRecord] = []
    for barcode, group in grouped.items():
        if len(group) == 1:
            unique.append(group[0])
            continue
        issues.append(
            Issue(
                IssueCode.DUPLICATE_BARCODE,
                f"duplicate barcode {barcode}; ignoring every occurrence",
            )
        )
    return unique


def _assign(
    barcodes: list[BarcodeRecord],
    orders_by_id: dict[str, OrderRecord],
) -> tuple[dict[str, list[str]], int]:
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
