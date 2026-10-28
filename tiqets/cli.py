"""Command line for the voucher export."""

import argparse
import sys
from pathlib import Path

from tiqets import __version__
from tiqets.load import InputError
from tiqets.output import write_vouchers
from tiqets.process import generate

DEFAULT_ORDERS = Path("data/orders.csv")
DEFAULT_BARCODES = Path("data/barcodes.csv")
DEFAULT_OUTPUT = Path("output/vouchers.csv")


def main(argv: list[str] | None = None) -> int:
    """Run the export. Returns a process exit code."""
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        report = generate(DEFAULT_ORDERS, DEFAULT_BARCODES, top=args.top)
        write_vouchers(DEFAULT_OUTPUT, report)
    except InputError as exc:
        _log("ERROR", str(exc))
        return 1
    except OSError as exc:
        _log("ERROR", str(exc))
        return 1

    for issue in report.issues:
        _log("WARNING", issue.message)
    row_noun = "line" if len(report.lines) == 1 else "lines"
    issue_noun = "issue" if len(report.issues) == 1 else "issues"
    _log(
        "INFO",
        f"wrote {len(report.lines)} {row_noun} to {DEFAULT_OUTPUT}; "
        f"{len(report.issues)} validation {issue_noun}",
    )
    sys.stdout.write(report.render_stdout())
    if args.strict and report.issues:
        return 3
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tiqets",
        description=(
            "Join an orders export and a barcodes export into a voucher file. "
            "Each output line is one order: customer id, order id, and the "
            "barcodes to print. The top customers and the unused-barcode count "
            "are printed to stdout. Validation problems are printed to stderr "
            "and left out of the file."
        ),
        epilog=(
            "Exit codes: 0 file written, 1 the export could not be read or written, "
            "2 invalid arguments, 3 validation problems were found and --strict was set. "
            "With --strict the file is still written."
        ),
    )
    parser.add_argument(
        "--top",
        type=_positive_int,
        default=5,
        help="how many customers to print, ranked by tickets bought (default: 5)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 3 when any row fails validation; the voucher file is still written",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("expected an integer >= 1")
    return parsed


def _log(level: str, message: str) -> None:
    print(f"{level} {message}", file=sys.stderr)
