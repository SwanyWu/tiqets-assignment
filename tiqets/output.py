"""Write the voucher file atomically."""

import os
import tempfile
from pathlib import Path

from tiqets.models import Report


def write_vouchers(path: Path, report: Report) -> None:
    """Write the voucher lines to path, replacing any existing file.

    Args:
        path: Destination, usually data/output/vouchers.csv.
        report: Report whose lines are written. Ranking and issues are not.

    Returns:
        None.

    Raises:
        OSError: The directory could not be created or the file could not be written.

    Example:
        A line for customer 10 and order 1 becomes
        ``10, 1, [111, 222]\\n``.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            for line in report.lines:
                handle.write(line.render())
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
