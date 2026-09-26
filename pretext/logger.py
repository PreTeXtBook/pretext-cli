import datetime
from pathlib import Path
import sys
import logging
import logging.handlers
import re
from typing import Any, Optional, cast
import click_log

# EXIT is CLI-only: the wrap-up line a command logs right before handing off
# to `exit_command` (e.g. "Failed to build without errors.  Exiting...").  It
# announces that the run is stopping; it isn't itself an error, so CRITICAL
# was too strong, and keeping it below ERROR keeps it out of
# error_flush_handler's buffer, so it isn't repeated in the flushed report.
EXIT_LEVEL = 35
logging.addLevelName(EXIT_LEVEL, "exit")


class PretextLogger(logging.Logger):
    """A `Logger` that also knows how to log at EXIT_LEVEL."""

    def exit(self, message: object, *args: Any, **kwargs: Any) -> None:
        self.log(EXIT_LEVEL, message, *args, **kwargs)


logging.setLoggerClass(PretextLogger)
log = cast(PretextLogger, logging.getLogger("ptxlogger"))
# Modules elsewhere (including core) fetch "ptxlogger" by name; whichever of
# them runs first decides the class.  Retag the singleton so `log.exit` exists
# no matter the import order, then restore the default for everyone else.
log.__class__ = PretextLogger
logging.setLoggerClass(logging.Logger)


class ColorFormatter(click_log.ColorFormatter):
    """click_log prefixes a message with its level name, but only for the levels
    in its own `colors` table; an unrecognized level gets no label at all.  Core
    PreTeXt renames level 50 to FATAL and adds BUG (45) and FALLBACK (25), so
    those messages arrived unlabeled.  Extend the table to cover them, along
    with the CLI's own EXIT level above.
    """

    colors = {
        **click_log.ColorFormatter.colors,
        "fatal": dict(fg="red", bold=True),
        "bug": dict(fg="magenta"),
        "fallback": dict(fg="cyan"),
        "exit": dict(fg="red"),
    }


def add_log_stream_handler() -> None:
    # Set up logging:
    # click_handler logs all messages to stdout as the CLI runs
    click_handler = logging.StreamHandler(sys.stdout)
    click_handler.setFormatter(ColorFormatter())
    log.addHandler(click_handler)


def get_log_error_flush_handler() -> logging.handlers.MemoryHandler:
    # error_flush_handler captures error/critical logs for flushing to stderr at the end of a CLI run
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(ColorFormatter())
    sh.setLevel(logging.ERROR)
    error_flush_handler = logging.handlers.MemoryHandler(
        capacity=1024 * 100,
        flushLevel=100,
        target=sh,
        flushOnClose=False,
    )
    error_flush_handler.setLevel(logging.ERROR)
    log.addHandler(error_flush_handler)
    return error_flush_handler


# Run logs are named by the time they were started (see add_log_file_handler).
# Other files in the logs folder (schema-errors.log, validation reports) don't
# match this and are never pruned.
TIMESTAMPED_LOG_PATTERN = re.compile(r"^\d{8}-\d{6}\.log$")
LOG_TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"
# A run log is removed only once it is older than this many days *and* not
# among the most recent LOGS_ALWAYS_KEPT logs.
LOG_RETENTION_DAYS = 7
LOGS_ALWAYS_KEPT = 5


def _log_timestamp(path: Path) -> Optional[datetime.datetime]:
    try:
        return datetime.datetime.strptime(path.stem, LOG_TIMESTAMP_FORMAT)
    except ValueError:
        # Matches the pattern but isn't a real date (e.g. month 13); leave it be.
        return None


def logs_to_remove(logs: list[Path]) -> list[Path]:
    """
    Given the timestamped run logs in the logs folder, sorted oldest first,
    return the ones that should be deleted.
    """
    cutoff = datetime.datetime.now() - datetime.timedelta(days=LOG_RETENTION_DAYS)
    candidates = logs[:-LOGS_ALWAYS_KEPT] if LOGS_ALWAYS_KEPT > 0 else logs
    return [
        path
        for path in candidates
        if (stamp := _log_timestamp(path)) is not None and stamp < cutoff
    ]


def prune_old_logs(log_folder_path: Path) -> None:
    """Remove old timestamped run logs, keeping only recent ones."""
    # The timestamp format sorts lexicographically in chronological order.
    logs = sorted(
        path
        for path in log_folder_path.iterdir()
        if path.is_file() and TIMESTAMPED_LOG_PATTERN.match(path.name)
    )
    for path in logs_to_remove(logs):
        try:
            path.unlink()
        except OSError as e:
            # Losing an old log is never worth failing a run over.
            log.debug(f"Could not remove old log file {path}: {e}")


def add_log_file_handler(log_folder_path: Path) -> None:
    # create file handler which logs even debug messages
    log_folder_path.mkdir(exist_ok=True)
    prune_old_logs(log_folder_path)
    logfile = (
        log_folder_path
        / f"{datetime.datetime.now().strftime(LOG_TIMESTAMP_FORMAT)}.log"
    )
    fh = logging.FileHandler(logfile, mode="w")
    fh.setLevel(logging.DEBUG)
    file_log_format = logging.Formatter("{levelname:<8}: {message}", style="{")
    fh.setFormatter(file_log_format)
    log.addHandler(fh)
