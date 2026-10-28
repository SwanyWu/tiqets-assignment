# Tiqets voucher export

Build the file used to print vouchers. One line per order: the customer, the order, and the barcodes on that order. Customer 10's first two orders in the file are:

```text
10, 1, [11111111111, 11111111318, 11111111428]
10, 18, [11111111128, 11111111335, 11111111445]
```

The job also prints the five customers who bought the most tickets, and how many barcodes are still unsold.

## Run

Python 3.12 or newer. The program uses the standard library only. From this directory:

```bash
python main.py
```

That reads `data/orders.csv` and `data/barcodes.csv` and writes `output/vouchers.csv`. The same command with explicit paths:

```bash
python -m tiqets \
  --orders data/orders.csv \
  --barcodes data/barcodes.csv \
  --output output/vouchers.csv
```

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

Rows that fail validation are written to stderr and left out of the file. A summary line on stderr reports how many voucher lines were written.

```text
WARNING duplicate barcode 11111111674; ignoring every occurrence
WARNING order 75 for customer 72 has no barcodes; ignoring
INFO wrote 204 lines to output/vouchers.csv; 8 validation issues
```

`--strict` still writes the file, then exits 3 when any row was skipped. Without `--strict` a completed file is exit 0. Exit 1 means an export could not be read or the output could not be written. Exit 2 means the arguments are invalid.

| Flag | Default | Purpose |
| --- | --- | --- |
| `--orders` | `data/orders.csv` | Orders export |
| `--barcodes` | `data/barcodes.csv` | Barcodes export |
| `--output` | `output/vouchers.csv` | Voucher file |
| `--top` | `5` | How many customers to print |
| `--strict` | off | Exit 3 when validation finds a problem |

Install the `tiqets` command and the test runner with `pip install -e ".[dev]"`. Running `python main.py` does not require that install.

## Input

Both files are UTF-8 CSV with a header row. Column names are case-insensitive. A trailing comma on the header is ignored. Blank lines are ignored.

`orders.csv`

| Column | Required | Meaning |
| --- | --- | --- |
| `order_id` | yes | Order. One row per order. |
| `customer_id` | yes | Customer who placed the order. |

`barcodes.csv`

| Column | Required | Meaning |
| --- | --- | --- |
| `barcode` | yes | Ticket code. Unique across the file. |
| `order_id` | no | Order this barcode was sold on. Blank means it is still in stock. |

Whitespace around a field is removed. An all-digit id is then compared numerically, so `007` and `7` are the same order, and the voucher file writes it without leading zeros. Barcodes keep every other character, including leading zeros.

## Output

`output/vouchers.csv` has no header. Each line is:

```text
customer_id, order_id, [barcode1, barcode2, ...]
```

There is a space after each comma. The barcode list is wrapped in brackets and is not CSV-quoted, so a split on every comma will break the list apart. Split into three fields: customer id, order id, and the remainder.

Lines are sorted by customer id, then order id. Barcodes inside a line are sorted alphabetically. The same exports always produce the same file, including when the export rows arrive in a different order. A customer with several orders appears on several lines.

Stdout, after the voucher file has been written:

```text
top <n> customers | #tickets
customer_id, amount_of_tickets
unused barcodes: <count>
```

`amount_of_tickets` is the number of barcodes on that customer's printed orders. Ties are broken by customer id, lowest first. Customers with no printed tickets are omitted. If fewer than five customers bought tickets, every one of them is printed.

## Validation

A row that fails a check is logged to stderr and ignored. The other rows are still written.

| Check | `IssueCode` | What is ignored |
| --- | --- | --- |
| Duplicate barcode | `duplicate_barcode` | Every row with that barcode, sold or unsold. The code is not printed and is not counted as stock. |
| Order with no barcodes | `order_without_barcodes` | The order. This includes an order whose barcodes were all removed as duplicates. |

On the bundled exports this removes 8 records: 5 duplicate barcodes (`11111111595`, `11111111649`, `11111111665`, `11111111674`, `11111111700`) and 3 orders with no barcodes (orders `75`, `108`, and `201`). 103 barcode rows have a blank order id. Five of those codes also appear on a sold row, so both copies are dropped. 98 barcodes remain in stock.

These checks are commented out. The bundled exports do not contain a row that would trigger them:

| Check | `IssueCode` | What it would ignore |
| --- | --- | --- |
| Missing id, or a value containing a comma, bracket, or newline | `invalid_row` | That row. Those characters would make the voucher line ambiguous. |
| Duplicate order id | `duplicate_order` | Every row with that order id. |
| Barcode pointing at a duplicate order | `rejected_order` | That barcode. |
| Barcode whose order is not in the orders file | `unknown_order` | That barcode. |

Customers 29 and 60 have both bought 16 tickets. Customer 29 is printed first.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

`tests/test_process.py` and `tests/test_load.py` cover the validation rules. `tests/test_dataset.py` runs the bundled exports and checks the ranking, the unused count, and that the duplicate barcodes and the empty orders are absent from the file. `tests/test_cli.py` covers exit codes and the output file.

## Project layout

```text
main.py                 run from the repository root
tiqets/                 loader, validation, join, command line
data/                   bundled exports
tests/                  unit tests and the bundled-export check
sql/schema.sql          tables, keys, indexes
sql/queries.sql         voucher file, top 5, unused count
docs/data_model.md      relations and why each index exists
docs/deployment.md      container, schedule, exit codes, rollback
```

## With pandas

Set the production shell aside and the same result is a short pandas script: load the two CSVs, join them, and filter.

1. Read both files. A blank `order_id` on a barcode comes in as missing, which is unsold stock.
2. Drop every copy of a duplicated barcode (`drop_duplicates(keep=False)`). Log those values. The rows left with no order id are the unused count.
3. Left-join the sold barcodes onto the orders. Rows with no barcode are the orders that have nothing to print. Log those order ids and drop them.
4. Group by `customer_id` and `order_id`, and aggregate the barcodes into a list. Each group is one voucher line.
5. A customer's ticket count is the sum of those list lengths. Sort by that count and take the top 5.

The bracketed line (`10, 1, [111, 222]`) is printed by a small loop after the group-by. Selecting the bad rows is pandas. Writing those rows to stderr is ordinary Python around that selection.

The records, the issue codes, the atomic write, and the tests wrap that join for a batch job. They are separate from the data steps.

## Deploy

The job is a container that reads two mounted files and writes one. Build, schedule, alerting, and rollback are in [docs/deployment.md](docs/deployment.md). The relational model is in [docs/data_model.md](docs/data_model.md).
