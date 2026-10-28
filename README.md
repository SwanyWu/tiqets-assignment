# Tiqets voucher generator

This project reads `orders.csv` and `barcodes.csv` to
- generate `vouchers.csv`.
- print top `<N>` customers who bought the most tickets
- the number of barcodes are still unsold.

It needs Python 3.12 or newer and standard library.

> [!NOTE]
> There are plenty of ways to over-engineer this. `Pandas` library is enough to join the two files and filter them, but that little script is not something you'd actually run in production. You'd want audit logs, error handling, monitoring, alerting, a database, maybe an API to hand the vouchers out, and Kubernetes or Terraform so the whole thing sits in CI/CD.
>
> I thought about all of that, then kept the simple version. It's the thought that counts :)

## Run

From this directory (N is an optional integer that defaults to 5):

```bash
python main.py --top <N>
```
or
```bash
python -m tiqets --top <N>
```
Stdout is the ranking and #unused barcodes:

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
...
WARNING order 75 for customer 72 has no barcodes; ignoring
INFO wrote 204 lines to output/vouchers.csv; 8 validation issues
```

## Validation

A row that fails a check is logged to stderr and ignored. The other rows are still written.

| Check | `IssueCode` | What is ignored |
| --- | --- | --- |
| Duplicate barcode | `duplicate_barcode` | Every row with that barcode, sold or unsold. The code is not printed and is not counted as stock. |
| Order with no barcodes | `order_without_barcodes` | The order. This includes an order whose barcodes were all removed as duplicates. |


## Tests

```bash
uv sync --extra dev
uv run pytest
```

`tests/test_process.py` and `tests/test_load.py` cover the validation rules. `tests/test_dataset.py` runs the bundled exports and checks the ranking, the unused count, and that the duplicate barcodes and the empty orders are absent from the file. `tests/test_cli.py` covers exit codes and the output file.

## Data model

The customer, order, and barcode relations are in [docs/data_model.md](docs/data_model.md).

## Deployment Plan

How the job is built, scheduled, and rolled back is in [docs/deployment.md](docs/deployment.md).