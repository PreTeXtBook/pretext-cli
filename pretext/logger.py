import sys
import logging
import click_log

log = logging.getLogger("ptxlogger")

# Set up logging:
# click_handler logs all messages to stdout as the CLI runs
click_handler = logging.StreamHandler(sys.stdout)
click_handler.setFormatter(click_log.ColorFormatter())
log.addHandler(click_handler)

# error_flush_handler captures error/critical logs for flushing to stderr at the end of a CLI run
sh = logging.StreamHandler(sys.stderr)
sh.setFormatter(click_log.ColorFormatter())
sh.setLevel(logging.ERROR)
error_flush_handler = logging.handlers.MemoryHandler(
    capacity=1024 * 100,
    flushLevel=100,
    target=sh,
    flushOnClose=False,
)
error_flush_handler.setLevel(logging.ERROR)
log.addHandler(error_flush_handler)
