# Deployment

This is a batch job. It reads two exports, writes one voucher file, and exits. It does not stay running and it does not open a port.

## What gets deployed

The container image contains the program only. Order and barcode files are mounted at run time. Customer data is not baked into the image.

```bash
docker build -t tiqets-vouchers:1.0.0 .
mkdir -p output
docker run --rm \
  -u "$(id -u):$(id -g)" \
  -v "$PWD/data:/app/data:ro" \
  -v "$PWD/output:/app/output" \
  tiqets-vouchers:1.0.0
```

`-u` writes the file as the user who launched the job. The image itself runs as uid `10001` when `-u` is omitted. The orders and barcodes mounts are read-only.

The same command without Docker, from a checkout:

```bash
python main.py
```

## Schedule

Run it after both exports for the day have landed. Either file being missing is exit code 1, so the job is safe to start only once both paths exist.

A scheduler runs the container the same way. The program always writes `output/vouchers.csv`. One run at a time is enough: a second run replaces that file atomically, but two overlapping runs can race on that rename. Take a lock in the scheduler. After exit 0, copy the file if you want a dated record:

```text
output/vouchers-2026-10-27.csv
```

Point the print process at the new copy only after the process exits 0.

## Exit codes and alerting

| Code | Meaning | What to do |
| --- | --- | --- |
| 0 | File written. | Print it. Also read stderr: validation warnings can still be present. |
| 1 | An export is missing, unreadable, or has the wrong header, or the output path could not be written. | Retry once the files are in place. No voucher file is written on a read failure. |
| 2 | The arguments are invalid. | Fix the command. This code comes from the argument parser. |
| 3 | `--strict`, and at least one row failed validation. The file is still written. | Page someone to repair the export. The file contains only the valid rows. |

Default mode exits 0 when the file was written, including when some rows were skipped. Stderr still lists every skipped row. Alert on any `WARNING` line even when the exit code is 0, or pass `--strict` if a dirty export should fail the job.

Stdout is the top-customers report. Capture it for the ranking, and give the print pipeline the output path.

## Same input, same file

Lines are sorted by customer id and order id. Barcodes on a line are sorted alphabetically. Reordering rows in the export does not change the voucher file. A rerun is safe.

The file is written to a temporary file in the output directory and renamed into place. Readers never see a partial file. The crash window is the moment before the rename: the previous voucher file is still intact, and the temporary file is removed if the write fails. The temporary file is mode `0600`.

## Rollback

Keep the previous dated file. If a run is wrong, point the printer back at that path. Do not edit the voucher file in place. Fix the export and rerun.

The image tag is the release. Roll back by running the previous image tag against the same exports. This container writes a file. The SQL schema in `sql/` is the storage model for when these rows live in a database.

## Data

The files contain customer identifiers and ticket codes. Treat the export directory and `output/` as personal data:

- mount exports read-only
- do not log the successful voucher lines; stderr logs only the rows that failed validation
- keep the output file mode `0600`
- do not commit `output/` or the raw exports to a public repository if they contain real customers

Both files are loaded into memory. Duplicate detection has to see every barcode before it can decide which rows to drop, so a streaming pass would still need a full copy of the keys. That is appropriate for these exports. If a future export is larger than the job's memory, load the files into the database in [`sql/schema.sql`](../sql/schema.sql) and let the barcode primary key reject duplicates. The voucher file is then the query in [`sql/queries.sql`](../sql/queries.sql).

## Shipping a change

1. Add or adjust a test in `tests/` that fails on the old behavior.
2. `pytest` must pass. The workflow in `.github/workflows/test.yml` runs the same command on Python 3.12.
3. Build `tiqets-vouchers:<version>` from the release commit.
4. Run it once on a copy of the latest exports and compare the voucher file and the stdout ranking with the previous run before the printer uses it.
