"""
Unit tests for `pretext.logger`.
"""

import datetime
import typing as t
import pytest
from pathlib import Path
from pretext import logger


def test_prune_old_logs_only_considers_run_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_logs = ["20260101-120000.log", "20250101-120000.log", "20260926-080000.log"]
    others = ["schema-errors.log", "schema-assembled-source.xml", "notes.log"]
    for name in run_logs + others:
        (tmp_path / name).write_text("")

    seen: t.List[Path] = []

    def remove_all(logs: t.List[Path]) -> t.List[Path]:
        seen.extend(logs)
        return logs

    monkeypatch.setattr(logger, "logs_to_remove", remove_all)
    logger.prune_old_logs(tmp_path)

    # The policy sees only timestamped run logs, oldest first...
    assert [p.name for p in seen] == sorted(run_logs)
    # ...so even a policy that removes everything leaves the other files alone.
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(others)


def _log_name(days_ago: float) -> str:
    stamp = datetime.datetime.now() - datetime.timedelta(days=days_ago)
    return f"{stamp.strftime(logger.LOG_TIMESTAMP_FORMAT)}.log"


def _remaining(tmp_path: Path) -> t.List[str]:
    return sorted(p.name for p in tmp_path.iterdir())


def test_prune_old_logs_keeps_last_week(tmp_path: Path) -> None:
    recent = [_log_name(d) for d in range(7)]
    old = [_log_name(d) for d in (8, 30, 400)]
    for name in recent + old:
        (tmp_path / name).write_text("")
    logger.prune_old_logs(tmp_path)
    assert _remaining(tmp_path) == sorted(recent)


def test_prune_old_logs_always_keeps_newest_five(tmp_path: Path) -> None:
    # All old: only the newest five survive.
    names = [_log_name(d) for d in range(10, 20)]
    for name in names:
        (tmp_path / name).write_text("")
    logger.prune_old_logs(tmp_path)
    assert _remaining(tmp_path) == sorted(names)[-5:]


def test_prune_old_logs_ignores_impossible_timestamps(tmp_path: Path) -> None:
    for name in ["20251399-000000.log"] + [_log_name(d) for d in range(10, 20)]:
        (tmp_path / name).write_text("")
    logger.prune_old_logs(tmp_path)
    assert "20251399-000000.log" in _remaining(tmp_path)
