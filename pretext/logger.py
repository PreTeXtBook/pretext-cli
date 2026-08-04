import datetime
from pathlib import Path
import sys
import logging
import logging.handlers
import click_log

log = logging.getLogger("ptxlogger")


class ColorFormatter(click_log.ColorFormatter):
    """click_log prefixes a message with its level name, but only for the levels
    in its own `colors` table; an unrecognized level gets no label at all.  Core
    PreTeXt renames level 50 to FATAL and adds BUG (45) and FALLBACK (25), so
    those messages arrived unlabeled.  Extend the table to cover them.
    """

    colors = {
        **click_log.ColorFormatter.colors,
        "fatal": dict(fg="red", bold=True),
        "bug": dict(fg="magenta"),
        "fallback": dict(fg="cyan"),
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


def add_log_file_handler(log_folder_path: Path) -> None:
    # create file handler which logs even debug messages
    log_folder_path.mkdir(exist_ok=True)
    logfile = (
        log_folder_path / f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
    )
    fh = logging.FileHandler(logfile, mode="w")
    fh.setLevel(logging.DEBUG)
    file_log_format = logging.Formatter("{levelname:<8}: {message}", style="{")
    fh.setFormatter(file_log_format)
    log.addHandler(fh)

def print_logs(log_level="info") -> None:
    levels = {
        "info": logging.INFO,
        "debug": logging.DEBUG,
    }
    if log_level.lower() not in levels.keys():
        raise ValueError(f"invalid log_level: {log_level}")
        return
    log = logging.getLogger("ptxlogger")
    logger.add_log_stream_handler()
    log.setLevel(levels[log_level.lower()])
    return
