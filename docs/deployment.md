# Deployment

This program runs once and exits. It reads `data/orders.csv` and `data/barcodes.csv`, writes `output/vouchers.csv`, prints the ranking on stdout, and prints skipped rows on stderr. It does not stay running and it does not open a port.

> [!NOTE]
> There are many ways to over-engineer this simple project. The steps below show how to deploy this in-memory, one-off app. In reality we need a database to deduplicate, keep track of history, and so on, and perhaps a cronjob (for example on Kubernetes) to keep generating the voucher.

## Image

`Dockerfile` builds an image with Python 3.12, `main.py`, and the `tiqets` package. The program uses the standard library, so the image does not install pandas. The orders and barcodes files are not copied into the image. They are mounted at run time.

The image process is user `vouchers`, uid `10001`. The only argument is `--top` (default 5).

## Build and run

From the repository root:

```bash
docker build -t tiqets-vouchers:1.0.0 .
mkdir -p output
docker run --rm \
  -u "$(id -u):$(id -g)" \
  -v "$PWD/data:/app/data:ro" \
  -v "$PWD/output:/app/output" \
  tiqets-vouchers:1.0.0
```

`-u` makes the voucher file owned by the user who launched the run. Without it, the process is uid `10001` and can write `output/` only when that directory allows that user. The data mount is read-only.

Pass `--top` the same way as `python main.py`:

```bash
docker run --rm \
  -u "$(id -u):$(id -g)" \
  -v "$PWD/data:/app/data:ro" \
  -v "$PWD/output:/app/output" \
  tiqets-vouchers:1.0.0 --top 5
```

The same run without Docker, from a checkout:

```bash
python main.py
```

## Exit codes

| Code | Meaning | What to do |
| --- | --- | --- |
| 0 | File written. | Print it. Also read stderr: validation warnings can still be present. |
| 1 | An export is missing, unreadable, or has the wrong header, or the output path could not be written. | Retry once the files are in place. No voucher file is written on a read failure. |
| 2 | The arguments are invalid. | Fix the command. This code comes from the argument parser. |

The process exits 0 when the file was written, including when some rows were skipped. Stderr still lists every skipped row. Alert on any `WARNING` line.

Stdout is the top-customers report. Capture it for the ranking, and give the print pipeline the output path.

## Same input, same file

Lines are sorted by customer id, then order id, both as text. Barcodes on a line are sorted as text. Reordering rows in the export does not change the voucher file. A rerun with the same image and the same exports is safe.

## Rollback

Keep the previous dated file. If a run is wrong, point the printer back at that path. Do not edit the voucher file in place. Fix the export and rerun.

The image tag is the release. Roll back by running the previous image tag against the same exports.

## Data

The files contain customer identifiers and ticket codes. Treat the export directory and `output/` as personal data:

- mount exports read-only
- do not log the successful voucher lines; stderr logs only the rows that failed validation
- the voucher file is created with mode `0600` on Unix
- do not commit `output/` or the raw exports to a public repository if they contain real customers

Both files are loaded into memory. Duplicate detection has to see every barcode before it can decide which rows to drop.
