from __future__ import annotations
from dataclasses import dataclass
from http.server import SimpleHTTPRequestHandler
import logging
import os
from pathlib import Path
import socketserver
import subprocess
import sys
import typing as t
import psutil

from pretext.utils import hash_path, home_path

# Get access to logger
log = logging.getLogger("ptxlogger")

# Limit for how many entries to allow in the server file
# before attempting to clean up non-running entries.
# Note: This is not a limit to the number of concurrent servers.
PURGE_LIMIT = 10


@dataclass
class RunningServerInfo:
    """A simple dataclass to hold the information in the running servers file."""

    path_hash: str
    pid: int
    port: int
    binding: str

    @staticmethod
    def from_file_line(line: str) -> RunningServerInfo:
        try:
            (path_hash, pid, port, binding) = line.split()
        except ValueError:
            # We only call this function when line.strip() is true, so line is not empty
            log.debug(f"Invalid line in running servers file: {line}")
            raise
        return RunningServerInfo(
            path_hash=path_hash, pid=int(pid), port=int(port), binding=binding
        )

    def to_file_line(self) -> str:
        return f"{self.path_hash} {self.pid} {self.port} {self.binding}\n"

    def is_active_server(self) -> bool:
        """Returns whether the server represented by this object is active on the provided port"""
        try:
            p = psutil.Process(self.pid)
        except psutil.NoSuchProcess:
            log.debug(f"Found entry no longer exists {self.pid}; removing entry.")
            remove_server_entry(self.path_hash)
            return False
        if not p.is_running():
            log.debug(f"Found entry no longer running {p.pid}; removing entry.")
            remove_server_entry(self.path_hash)
            return False
        if p.status == psutil.STATUS_ZOMBIE:
            log.debug(f"Found zombie process {p.pid}; removing entry.")
            remove_server_entry(self.path_hash)
            return False
        for _, _, _, laddr, _, _ in p.net_connections("all"):
            if isinstance(laddr, str):
                log.error(
                    f"BUG: the `pretext view` command encountered an error.  Please report this: process {self.pid} with laddr {laddr}"
                )
                continue
            elif isinstance(laddr.port, int) and laddr.port == self.port:
                log.info(f"Found PreTeXt web server at {self.url()}")
                return True
            else:
                log.debug(f"Found process {self.pid} with laddr {laddr}")
        log.debug(
            f"Found process {self.pid} no longer listening on specified port {self.port}"
        )
        return False

    def terminate(self) -> None:
        """Attempt to terminate the process described by this info."""
        try:
            log.debug(f"Terminating {self.pid}")
            remove_server_entry(self.path_hash)
            psutil.Process(self.pid).terminate()
        except Exception as e:
            log.error(
                f"Attempt to terminate PreTeXt web server failed for process {self.pid} on port {self.port}."
            )
            log.debug(e, exc_info=True)

    def url(self) -> str:
        return f"{self.binding}:{self.port}"


def is_port_in_use(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def get_running_servers() -> t.List[RunningServerInfo]:
    """
    Processes the ~/.ptx/running_servers file to retrieve a list
    of any possibly current running servers.
    """
    if not home_path().exists():
        return []
    try:
        running_servers_file = home_path() / "running_servers"
        if not running_servers_file.is_file():
            return []
        with open(running_servers_file, "r") as f:
            return [
                RunningServerInfo.from_file_line(line)
                for line in f.readlines()
                if line.strip()
            ]
    except IOError as e:
        log.error(
            f"Unable to open list of running PreTeXt web servers expected at ({running_servers_file})."
        )
        log.debug(e, exc_info=True)
        return []


def save_running_servers(running_servers: t.List[RunningServerInfo]) -> None:
    """
    Overwrites the ~/.ptx/running_servers file to store
    the new list of running servers.
    """
    # Ensure home path exists
    os.makedirs(home_path(), exist_ok=True)
    try:
        running_servers_file = home_path() / "running_servers"
        with open(running_servers_file, "w") as f:
            # Write each server info to a new line
            f.writelines([info.to_file_line() for info in running_servers])
    except IOError as e:
        log.error("Unable to write running servers file.")
        log.debug(e, exc_info=True)


def add_server_entry(path_hash: str, pid: int, port: int, binding: str) -> None:
    """Add a new server entry to ~/.ptx/running_servers.

    This function does not attempt to ensure that an active server doesn't already exist.
    """
    running_servers = get_running_servers()
    new_entry = RunningServerInfo(
        path_hash=path_hash, pid=pid, port=port, binding=binding
    )
    running_servers.append(new_entry)
    if len(running_servers) >= PURGE_LIMIT:
        log.info(f"There are {PURGE_LIMIT} or more servers on file. Cleaning up ...")
        running_servers = list(stop_inactive_servers(running_servers))
    save_running_servers(running_servers)
    log.info(f"Added pretext web server entry {new_entry.to_file_line()}")


def remove_server_entry(path_hash: str) -> None:
    remaining_servers = [
        info for info in get_running_servers() if info.path_hash != path_hash
    ]
    save_running_servers(remaining_servers)


def stop_inactive_servers(
    servers: t.List[RunningServerInfo],
) -> t.Iterator[RunningServerInfo]:
    """Stops any inactive servers and yields the active ones."""
    for server in servers:
        if server.is_active_server():
            yield server
        else:
            server.terminate()


def active_server_for_path_hash(path_hash: str) -> t.Optional[RunningServerInfo]:
    return next(
        (info for info in get_running_servers() if info.path_hash == path_hash),
        None,
    )


# boilerplate to prevent overzealous caching by preview server, and
# avoid port issues
def binding_for_access(access: t.Literal["public", "private"] = "private") -> str:
    if access == "private":
        return "localhost"
    return "0.0.0.0"


def start_server(
    base_dir: Path,
    access: t.Literal["public", "private"] = "private",
    port: int = 8128,
    callback: t.Callable[[int], None] | None = None,
) -> None:
    log.info("setting up PreTeXt web server ...")
    path_hash = hash_path(base_dir)
    pid = os.getpid()
    binding = binding_for_access(access)
    log.debug("values set: %s, %s, %s", path_hash, binding, port)

    # Previously we defined a custom handler to prevent caching, but we don't need to do that anymore.  It was causing issues with the _static js/css files inside codespaces for an unknown reason.  Might bring this back in the future.
    # 2024-04-05: try using this again to let Firefox work
    class RequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args: t.Any, **kwargs: t.Any):
            super().__init__(*args, directory=base_dir.as_posix(), **kwargs)

        """HTTP request handler with no caching"""

        def end_headers(self) -> None:
            self.send_my_headers()
            SimpleHTTPRequestHandler.end_headers(self)

        def send_my_headers(self) -> None:
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")

    class TCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    while True:
        try:
            with TCPServer((binding, port), RequestHandler) as httpd:
                log.debug("adding PreTeXt web server entry")
                add_server_entry(path_hash, pid, port, binding)
                log.debug("Starting the PreTeXt web server")
                if callback is not None:
                    callback(port)
                httpd.serve_forever()
        except OSError:
            log.warning(f"Port {port} could not be used.")
            port += 1
            log.warning(f"Trying port {port} instead.\n")
        except KeyboardInterrupt:
            log.info("Stopping PreTeXt web server.")
            remove_server_entry(path_hash)
            return


def start_codespace_server(
    base_dir: Path,
    access: t.Literal["public", "private"] = "private",
    port: int = 8128,
    callback: t.Callable[[int], None] | None = None,
) -> None:
    while is_port_in_use(port):
        log.debug(f"Port {port} is in use.")
        port = port + 1
        log.debug(f"Trying port {port} instead.")
    path_hash = hash_path(base_dir)
    binding = binding_for_access(access)
    log.debug(f"values set: {path_hash}, {binding}, {port}")

    log.info("Starting PreTeXt web server")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port)], cwd=base_dir
    )
    log.debug(f"Server process pid: {server_process.pid}")
    log.debug("adding server entry")
    add_server_entry(path_hash, server_process.pid, port, binding)
    if callback is not None:
        callback(port)
    return
