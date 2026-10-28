"""Exit codes and the voucher file written by the command line."""

from pathlib import Path

import pytest

from tiqets import cli

ROOT = Path(__file__).resolve().parents[1]


def _point_at(monkeypatch: pytest.MonkeyPatch, orders: Path, barcodes: Path, output: Path) -> None:
    monkeypatch.setattr(cli, "DEFAULT_ORDERS", orders)
    monkeypatch.setattr(cli, "DEFAULT_BARCODES", barcodes)
    monkeypatch.setattr(cli, "DEFAULT_OUTPUT", output)


def test_success_writes_the_file_and_prints_the_ranking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "vouchers.csv"
    _point_at(
        monkeypatch,
        ROOT / "data" / "input" / "orders.csv",
        ROOT / "data" / "input" / "barcodes.csv",
        output,
    )

    assert cli.main([]) == 0

    assert output.read_text(encoding="utf-8").startswith("10, 1, [")
    captured = capsys.readouterr()
    assert "top 5 customers | #tickets\n10, 23\n" in captured.out
    assert "unused barcodes: 98\n" in captured.out
    assert "wrote 204 lines" in captured.err
    assert captured.err.count("WARNING") == 8


def test_clean_export_exits_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    orders = tmp_path / "orders.csv"
    barcodes = tmp_path / "barcodes.csv"
    output = tmp_path / "out" / "vouchers.csv"
    orders.write_text("order_id,customer_id\n1,10\n", encoding="utf-8")
    barcodes.write_text("barcode,order_id\n111,1\n", encoding="utf-8")
    _point_at(monkeypatch, orders, barcodes, output)

    assert cli.main(["--top", "1"]) == 0

    assert output.read_text(encoding="utf-8") == "10, 1, [111]\n"
    captured = capsys.readouterr()
    assert captured.out == "top 1 customers | #tickets\n10, 1\nunused barcodes: 0\n"
    assert "WARNING" not in captured.err


def test_missing_export_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _point_at(
        monkeypatch,
        tmp_path / "missing.csv",
        ROOT / "data" / "input" / "barcodes.csv",
        tmp_path / "vouchers.csv",
    )

    assert cli.main([]) == 1
    assert "ERROR" in capsys.readouterr().err


def test_invalid_top_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["--top", "0"])

    assert exc.value.code == 2
    assert "ERROR" not in capsys.readouterr().err
