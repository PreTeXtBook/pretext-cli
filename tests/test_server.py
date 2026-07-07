"""
Unit tests for `pretext.server`, the module that tracks locally running
preview servers (used by `pretext view`).

The server registry is a plain-text file (``~/.ptx/running_servers``) where
each line records ``path_hash pid port binding`` for one server.  These tests
exercise the registry bookkeeping in isolation:

- serialization of `RunningServerInfo` to/from registry lines,
- reading/writing the registry file, including edge cases (no home directory,
  missing file, blank lines),
- adding/removing entries and looking up the entry for a project,
- purging of dead entries once the registry grows past `PURGE_LIMIT`,
- small helpers (`binding_for_access`, `is_port_in_use`).

All tests monkeypatch `server.home_path` so nothing touches the real
``~/.ptx`` directory, and any "running" pids used are guaranteed-dead fake
pids so no real process is ever terminated.

The full server lifecycle (actually starting/stopping an HTTP server) is
covered end-to-end by ``test_cli.py::test_view``.
"""

import socket
from pathlib import Path

import pytest

from pretext import server

# A pid that (essentially) cannot belong to a real process: pid_max on Linux
# is at most 2^22, and Windows pids are far smaller.
DEAD_PID = 2**22 + 1


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the server registry to a temporary ``.ptx`` directory."""
    home = tmp_path / ".ptx"
    monkeypatch.setattr(server, "home_path", lambda: home)
    return home


def test_running_server_info_round_trip() -> None:
    """A registry line survives a to_file_line/from_file_line round trip."""
    info = server.RunningServerInfo(
        path_hash="abc123def4", pid=123, port=8128, binding="localhost"
    )
    line = info.to_file_line()
    assert server.RunningServerInfo.from_file_line(line) == info


def test_running_server_info_malformed_line_raises() -> None:
    """A malformed registry line (wrong number of fields) raises ValueError."""
    with pytest.raises(ValueError):
        server.RunningServerInfo.from_file_line("only three fields here-")


def test_running_server_info_url() -> None:
    """url() combines the binding and port."""
    info = server.RunningServerInfo(
        path_hash="abc", pid=1, port=8000, binding="localhost"
    )
    assert info.url() == "localhost:8000"


def test_get_running_servers_when_no_home_dir(fake_home: Path) -> None:
    """With no ~/.ptx directory at all, the registry reads as empty."""
    assert not fake_home.exists()
    assert server.get_running_servers() == []


def test_get_running_servers_when_no_registry_file(fake_home: Path) -> None:
    """With a ~/.ptx directory but no registry file, the registry is empty."""
    fake_home.mkdir()
    assert server.get_running_servers() == []


def test_get_running_servers_skips_blank_lines(fake_home: Path) -> None:
    """Blank lines in the registry file are ignored when reading."""
    fake_home.mkdir()
    (fake_home / "running_servers").write_text(
        f"\nhash1 {DEAD_PID} 8000 localhost\n\nhash2 {DEAD_PID} 8001 localhost\n\n"
    )
    servers = server.get_running_servers()
    assert [s.path_hash for s in servers] == ["hash1", "hash2"]


def test_save_and_get_running_servers_round_trip(fake_home: Path) -> None:
    """save_running_servers creates ~/.ptx and writes entries that read back."""
    infos = [
        server.RunningServerInfo(
            path_hash=f"hash{i}", pid=DEAD_PID + i, port=8000 + i, binding="localhost"
        )
        for i in range(3)
    ]
    server.save_running_servers(infos)
    assert server.get_running_servers() == infos


def test_add_and_remove_server_entry(fake_home: Path) -> None:
    """add_server_entry appends to the registry; remove_server_entry deletes
    only the entry with the matching path hash."""
    server.add_server_entry("hash-a", DEAD_PID, 8000, "localhost")
    server.add_server_entry("hash-b", DEAD_PID + 1, 8001, "localhost")
    assert [s.path_hash for s in server.get_running_servers()] == ["hash-a", "hash-b"]

    server.remove_server_entry("hash-a")
    remaining = server.get_running_servers()
    assert [s.path_hash for s in remaining] == ["hash-b"]
    assert remaining[0].port == 8001


def test_active_server_for_path_hash(fake_home: Path) -> None:
    """active_server_for_path_hash returns the matching entry, or None."""
    server.add_server_entry("hash-a", DEAD_PID, 8000, "localhost")
    found = server.active_server_for_path_hash("hash-a")
    assert found is not None
    assert found.port == 8000
    assert server.active_server_for_path_hash("no-such-hash") is None


def test_dead_entries_purged_at_limit(fake_home: Path) -> None:
    """Once the registry reaches PURGE_LIMIT entries, adding another purges
    entries whose process is no longer alive (all of them, here)."""
    for i in range(server.PURGE_LIMIT - 1):
        server.add_server_entry(f"hash{i}", DEAD_PID + i, 8000 + i, "localhost")
    assert len(server.get_running_servers()) == server.PURGE_LIMIT - 1
    # This addition hits the limit and triggers the purge of dead entries.
    server.add_server_entry("hash-last", DEAD_PID + 99, 9000, "localhost")
    assert server.get_running_servers() == []


def test_is_active_server_false_for_dead_pid_and_removes_entry(
    fake_home: Path,
) -> None:
    """is_active_server() detects a dead pid and cleans up its registry entry."""
    server.add_server_entry("hash-dead", DEAD_PID, 8000, "localhost")
    info = server.get_running_servers()[0]
    assert info.is_active_server() is False
    assert server.get_running_servers() == []


def test_stop_inactive_servers_keeps_active_ones(
    fake_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """stop_inactive_servers yields active servers and terminates the rest."""
    active = server.RunningServerInfo(
        path_hash="active", pid=1, port=8000, binding="localhost"
    )
    inactive = server.RunningServerInfo(
        path_hash="inactive", pid=2, port=8001, binding="localhost"
    )
    terminated = []
    monkeypatch.setattr(
        server.RunningServerInfo,
        "is_active_server",
        lambda self: self.path_hash == "active",
    )
    monkeypatch.setattr(
        server.RunningServerInfo,
        "terminate",
        lambda self: terminated.append(self.path_hash),
    )
    survivors = list(server.stop_inactive_servers([active, inactive]))
    assert survivors == [active]
    assert terminated == ["inactive"]


def test_binding_for_access() -> None:
    """Private access binds to localhost only; public binds to all interfaces."""
    assert server.binding_for_access("private") == "localhost"
    assert server.binding_for_access("public") == "0.0.0.0"


def test_is_port_in_use() -> None:
    """is_port_in_use reports True exactly while something listens on the port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        s.listen(1)
        port = s.getsockname()[1]
        assert server.is_port_in_use(port)
    assert not server.is_port_in_use(port)
