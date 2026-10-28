# Tiqets voucher export

Build the file used to print vouchers. One line per orders row: the customer, the order, and the barcodes on that order. The same run prints the customers who bought the most tickets, and how many barcodes are still unsold.

Python 3.12 or newer. `python main.py` uses the standard library only.

## Run

From this directory:

```bash
python main.py
```

`python -m tiqets` does the same thing. Both read `data/orders.csv` and `data/barcodes.csv`, and write `output/vouchers.csv`. Those paths are relative to the working directory.

Stdout is the ranking:

```text
top 5 customers | #tickets
10, 23
56, 20
29, 16
60, 16
59, 15
unused barcodes: 98
```

Rows that fail validation are written to stderr and left out of the file. A summary line reports how many voucher lines were written.

```text
WARNING duplicate barcode 11111111674; ignoring every occurrence
WARNING order 75 for customer 72 has no barcodes; ignoring
INFO wrote 204 lines to output/vouchers.csv; 8 validation issues
```

`--strict` still writes the file, then exits 3 when any row was skipped. Without `--strict` a completed file is exit 0. Exit 1 means an export could not be read or the output could not be written. Exit 2 means the arguments are invalid.

| Flag | Default | Purpose |
| --- | --- | --- |
| `--top` | `5` | How many customers to print |
| `--strict` | off | Exit 3 when validation finds a problem |
| `--version` | | Print the version and exit |

## Input

Both files are UTF-8 CSV with a header row. Column names are case-insensitive. A trailing comma on the header is ignored. Blank lines are ignored. Whitespace around a field is removed. Ids stay text, including leading zeros, so `007` and `7` are different orders. Barcodes keep every character, including leading zeros.

`orders.csv`

| Column | Required | Meaning |
| --- | --- | --- |
| `order_id` | yes | Order. |
| `customer_id` | yes | Customer who placed the order. |

`barcodes.csv`

| Column | Required | Meaning |
| --- | --- | --- |
| `barcode` | yes | Ticket code. Unique across the file. |
| `order_id` | no | Order this barcode was sold on. Blank means it is still in stock. |

## Output

`output/vouchers.csv` has no header. Each line is:

```text
customer_id, order_id, [barcode1, barcode2, ...]
```

There is a space after each comma. The barcode list is wrapped in brackets and is not CSV-quoted. Customer 10's first two lines are:

```text
10, 1, [11111111111, 11111111318, 11111111428]
10, 139, [11111111248, 11111111565]
```

Lines are sorted by customer id, then order id, both as text, so `139` comes before `18`. Barcodes inside a line are sorted as text. The same rows produce the same file when the export arrives in a different order. Each orders row is printed at most once. A repeated order id is printed once per row, not collapsed.

Stdout, after the voucher file has been written:

```text
top <n> customers | #tickets
customer_id, amount_of_tickets
unused barcodes: <count>
```

`amount_of_tickets` is the number of barcodes on that customer's printed orders. Ties are broken by customer id as text, so customer 29 prints before customer 60. Customers with no printed tickets are omitted. If fewer customers bought tickets than `--top`, every one of them is printed.

## Validation

A row that fails a check is logged to stderr and ignored. The other rows are still written.

| Check | `IssueCode` | What is ignored |
| --- | --- | --- |
| Duplicate barcode | `duplicate_barcode` | Every row with that barcode, sold or unsold. The code is not printed and is not counted as stock. |
| Order with no barcodes | `order_without_barcodes` | The order. This includes an order whose barcodes were all removed as duplicates. |

A barcode whose order id is not in the orders file is dropped without a warning. It is not printed and it is not counted as stock.

On the bundled exports this removes 8 records: 5 duplicate barcodes (`11111111595`, `11111111649`, `11111111665`, `11111111674`, `11111111700`) and 3 orders with no barcodes (orders `75`, `108`, and `201`). 98 barcodes remain in stock.

## Tests

```bash
uv sync --extra dev
uv run pytest
```

`tests/test_process.py` and `tests/test_load.py` cover the validation rules. `tests/test_dataset.py` runs the bundled exports and checks the ranking, the unused count, and that the duplicate barcodes and the empty orders are absent from the file. `tests/test_cli.py` covers exit codes and the output file.

## Pandas script

`pandasscript/vouchers.py` is separate. It needs pandas, writes `output/vouchers_pandas.csv`, strips leading zeros from numeric ids, and sorts those ids numerically.

```bash
python pandasscript/vouchers.py
```
