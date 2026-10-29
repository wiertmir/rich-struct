"""Run: python examples/log_demo.py  (needs `pip install structlog`)"""

from pathlib import Path

from rich_struct.log import configure, get_logger

# Console logging is on by default; this also writes logs/log_demo_yyyy_mm_dd.log (a new file daily, last 7 kept).
# configure(console=False) would turn the console off; without configure() only the console is used.
configure(file=True)

log = get_logger()
position, elapsed = "A-17", 42

log.info("Module name: {}", __name__)
log.debug("Debug: started with %s and %d", Path("/tmp/data.csv"), 3)
log.info("Processed %s in %03d ms.", position, elapsed)
log.info("Processed {} in {:03d} ms.", position, elapsed)
log.info("Types: {} {} {} {} {} {}", "text", 12, 3.14, True, None, Path("/etc/hosts"))
log.info("Other objects: %s %s", [1, "two"], {"k": 1})
log.info("With fields", user="bob", retries=3, ok=False)
log.warning("Disk at %d%% on %s", 91, "/dev/sda1")
log.error("Failed to open %s", Path("/nope"), code=2)
log.critical("Shutting down")
try:
    1 / 0
except ZeroDivisionError as e:
    log.exception("Caught {!r}", e)
