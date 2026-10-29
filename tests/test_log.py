import pytest

pytest.importorskip("structlog")

from rich_struct.log import configure, get_logger


def lines(capsys):
    return capsys.readouterr().err.splitlines()


@pytest.mark.parametrize("fmt", ["Took %s in %03d ms.", "Took {} in {:03d} ms."])
def test_both_styles(capsys, monkeypatch, fmt):
    monkeypatch.setenv("NO_COLOR", "1")
    configure()
    get_logger().info(fmt, "x", 7)
    assert lines(capsys)[0].endswith("INFO     Took x in 007 ms.")


def test_level_and_bad_args(capsys, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    configure("warning")
    log = get_logger()
    log.info("hidden")
    log.error("bad %d", "x")  # must not raise
    assert lines(capsys)[0].endswith("ERROR    bad %d 'x'")
