"""Records shared by the loader, the join, and the command line."""

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class OrderRecord:
    order_id: str
    customer_id: str


@dataclass(frozen=True, slots=True)
class BarcodeRecord:
    barcode: str
    order_id: str | None


class IssueCode(StrEnum):
    DUPLICATE_BARCODE = "duplicate_barcode"
    ORDER_WITHOUT_BARCODES = "order_without_barcodes"

@dataclass(frozen=True, slots=True)
class Issue:
    code: IssueCode
    message: str

@dataclass(frozen=True, slots=True)
class ReadResult[T]:
    records: tuple[T, ...]
    issues: tuple[Issue, ...]


@dataclass(frozen=True, slots=True)
class VoucherLine:
    customer_id: str
    order_id: str
    barcodes: tuple[str, ...]

    def render(self) -> str:
        return f"{self.customer_id}, {self.order_id}, [{', '.join(self.barcodes)}]"


@dataclass(frozen=True, slots=True)
class Report:
    lines: tuple[VoucherLine, ...]
    top_customers: tuple[tuple[str, int], ...]
    unused_barcodes: int
    issues: tuple[Issue, ...]

    def render_stdout(self) -> str:
        rows = [f"top {len(self.top_customers)} customers | #tickets"]
        rows.extend(
            f"{customer_id}, {count}" for customer_id, count in self.top_customers
        )
        rows.append(f"unused barcodes: {self.unused_barcodes}")
        return "\n".join(rows) + "\n"
