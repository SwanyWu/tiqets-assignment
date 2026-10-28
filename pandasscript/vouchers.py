"""Same voucher export, as a short pandas script.

    pip install pandas
    python pandasscript/vouchers.py
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ORDERS_PATH = ROOT / "data" / "orders.csv"
BARCODES_PATH = ROOT / "data" / "barcodes.csv"
OUTPUT_PATH = ROOT / "output" / "vouchers_pandas.csv"
TOP = 5


def main() -> None:
    orders = _read(ORDERS_PATH)
    barcodes = _read(BARCODES_PATH)
    orders["order_id"] = _normalize(orders["order_id"])
    orders["customer_id"] = _normalize(orders["customer_id"])
    barcodes["barcode"] = barcodes["barcode"].str.strip()
    barcodes["order_id"] = _normalize(barcodes["order_id"])

    duplicated = barcodes["barcode"].duplicated(keep=False)
    for barcode in barcodes.loc[duplicated, "barcode"].drop_duplicates():
        print(
            f"WARNING duplicate barcode {barcode}; ignoring every occurrence",
            file=sys.stderr,
        )
    kept = barcodes.loc[~duplicated].copy()
    unused = int((kept["order_id"] == "").sum())
    sold = kept.loc[kept["order_id"] != ""]

    missing = orders.loc[~orders["order_id"].isin(sold["order_id"])]
    for row in missing.itertuples(index=False):
        print(
            f"WARNING order {row.order_id} for customer {row.customer_id} "
            "has no barcodes; ignoring",
            file=sys.stderr,
        )

    joined = orders.merge(sold, on="order_id", how="inner")
    grouped = (
        joined.groupby(["customer_id", "order_id"], sort=False)["barcode"]
        .agg(lambda codes: tuple(sorted(codes)))
        .reset_index()
    )
    grouped["_customer"] = grouped["customer_id"].map(_sort_key)
    grouped["_order"] = grouped["order_id"].map(_sort_key)
    grouped = grouped.sort_values(["_customer", "_order"])

    lines = [
        f"{row.customer_id}, {row.order_id}, [{', '.join(row.barcode)}]"
        for row in grouped.itertuples(index=False)
    ]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    tickets = joined.groupby("customer_id").size().reset_index(name="tickets")
    tickets["_customer"] = tickets["customer_id"].map(_sort_key)
    tickets = tickets.sort_values(
        by=["tickets", "_customer"],
        ascending=[False, True],
    ).head(TOP)

    issues = int(barcodes.loc[duplicated, "barcode"].nunique()) + len(missing)
    print(
        f"INFO wrote {len(lines)} lines to {OUTPUT_PATH.relative_to(ROOT)}; "
        f"{issues} validation issues",
        file=sys.stderr,
    )
    print(f"top {len(tickets)} customers | #tickets")
    for row in tickets.itertuples(index=False):
        print(f"{row.customer_id}, {row.tickets}")
    print(f"unused barcodes: {unused}")


def _read(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    return frame.apply(lambda column: column.str.strip())


def _normalize(values: pd.Series) -> pd.Series:
    stripped = values.str.strip()
    numeric = stripped.str.fullmatch(r"[0-9]+").fillna(False)
    normalized = stripped.str.lstrip("0").replace("", "0")
    return stripped.where(~numeric, normalized)


def _sort_key(value: object) -> tuple:
    text = str(value)
    if text.isdigit():
        return 0, int(text)
    return 1, text


if __name__ == "__main__":
    main()
