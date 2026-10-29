import pytest

pytest.importorskip("structlog")

from rich_struct.log import configure, get_logger


@pytest.fixture(autouse=True)
def gil_build(monkeypatch):
    monkeypatch.setattr("rich_struct.log._free_threaded", lambda: False)  # same output on every Python


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


def test_handler_gets_plain_line_with_utc_offset(capsys, tmp_path):
    import logging.handlers
    import re

    handler = logging.handlers.TimedRotatingFileHandler(tmp_path / "a.log", when="midnight", backupCount=7)
    configure(handler=handler)
    get_logger().info("Took {} ms", 7)
    handler.close()
    assert re.fullmatch(
        r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3}[+-]\d\d:\d\d INFO     `[\w.]+` Took 7 ms\n", (tmp_path / "a.log").read_text()
    )


def test_thread_name_when_free_threaded(capsys, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr("rich_struct.log._free_threaded", lambda: True)
    configure()
    get_logger().info("hi")
    assert lines(capsys)[0].endswith("INFO     [MainThread] hi")


class Job:
    def run(self):
        get_logger().info("x")


def test_file_line_has_module_and_class(tmp_path):
    import logging

    handler = logging.FileHandler(tmp_path / "a.log")
    configure(handler=handler)
    Job().run()
    handler.close()
    assert (tmp_path / "a.log").read_text().endswith(f"INFO     `{__name__}.Job` x\n")


def test_file_option_writes_dated_file(tmp_path, monkeypatch):
    from datetime import date

    monkeypatch.chdir(tmp_path)
    configure(file=True)
    get_logger().info("hi")
    (path,) = (tmp_path / "logs").glob("*.log")
    assert path.name.endswith(f"_{date.today():%Y_%m_%d}.log")
    assert path.read_text().endswith("INFO     `test_log` hi\n")


def test_console_off_and_file_off_by_default(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    configure(console=False)
    get_logger().info("hi")
    assert capsys.readouterr().err == "" and not (tmp_path / "logs").exists()


def test_old_files_are_pruned(tmp_path):
    from rich_struct.log import DailyFileHandler

    for day in range(1, 10):
        (tmp_path / f"app_2026_09_{day:02d}.log").touch()
    DailyFileHandler(tmp_path, "app", keep=7).close()
    assert len(list(tmp_path.glob("app_*.log"))) == 7
