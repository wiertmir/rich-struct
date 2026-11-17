import pytest

pytest.importorskip("structlog")

from rich_struct.log import configure, get_logger


@pytest.fixture(autouse=True)
def gil_build(monkeypatch):
    monkeypatch.setattr("rich_struct.log._free_threaded", lambda: False)  # same default on every Python


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


def test_thread_name_when_asked(capsys, monkeypatch):
    import threading

    monkeypatch.setenv("NO_COLOR", "1")
    configure(thread=True)
    worker = threading.Thread(target=lambda: get_logger().info("hi"), name="worker-1")
    worker.start()
    worker.join()
    assert lines(capsys)[0].endswith("INFO     [worker-1] hi")


def test_thread_name_by_default_only_when_free_threaded(capsys, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    configure()
    get_logger().info("hi")
    monkeypatch.setattr("rich_struct.log._free_threaded", lambda: True)
    configure()
    get_logger().info("hi")
    configure(thread=False)
    get_logger().info("hi")
    assert [line[13:] for line in lines(capsys)] == ["INFO     hi", "INFO     [MainThread] hi", "INFO     hi"]


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


def test_notebook_lines_share_one_block(capsys, monkeypatch):
    pytest.importorskip("IPython")
    import IPython.display

    shown = []

    class Handle:
        def update(self, bundle, raw):
            shown.append(bundle)

    handles = []

    def display(bundle, raw, display_id):
        shown.append(bundle)
        handles.append(Handle())
        return handles[-1]

    monkeypatch.setattr("rich_struct.log._in_notebook", lambda: True)
    sent = [0]  # what the kernel's message counter would say
    monkeypatch.setattr("rich_struct.log._block", {"mark": None, "handle": None, "html": [], "text": []})
    monkeypatch.setattr("rich_struct.log._kernel_mark", lambda: sent[0])
    monkeypatch.setattr(IPython.display, "display", display)
    configure()
    log = get_logger()
    log.info("one <b>")
    log.info("two")
    sent[0] += 1  # a print in between
    log.info("three")
    assert capsys.readouterr().err == ""
    lines_shown = [[line[13:] for line in b["text/plain"].splitlines()] for b in shown]
    assert lines_shown == [["INFO     one <b>"], ["INFO     one <b>", "INFO     two"], ["INFO     three"]]
    assert len(handles) == 2  # "three" went to a new block
    html = shown[1]["text/html"]
    assert html.count("<pre") == 1 and "one &lt;b&gt;" in html and "border:1px solid #" in html
