from __future__ import annotations
from dataclasses import dataclass
from http.server import SimpleHTTPRequestHandler
import logging
import os
from pathlib import Path
import socketserver
import typing as t
import psutil

from pretext.utils import hash_path, home_path

# Get access to logger
log = logging.getLogger("ptxlogger")


@dataclass
class RunningServerInfo:
    """A simple dataclass to hold the information in the running servers file."""

    pathHash: str
    pid: int
    port: int
    binding: str

    @staticmethod
    def fromFileLine(line: str) -> RunningServerInfo:
        (pathHash, pid, port, binding) = line.split()
        return RunningServerInfo(
            pathHash=pathHash, pid=int(pid), port=int(port), binding=binding
        )

    def toFileLine(self) -> str:
        return f"{self.pathHash} {self.pid} {self.port} {self.binding}"

    def isActiveServer(self) -> bool:
        """Returns whether the server represented by this object is active on the provided port"""
        p = psutil.Process(self.pid)
        if not p.is_running():
            log.info(f"Found entry no longer running {p.pid}")
            return False
        if p.status == psutil.STATUS_ZOMBIE:
            log.info(f"Found zombie process {p.pid}")
            return False
        for _, _, _, laddr, _, _ in p.net_connections("all"):
            if laddr == (self.binding, self.port):
                log.info(f"Found server at {self.url()}")
                return True
        log.info(
            f"Found process {self.pid} no longer listening on specified port {self.port}"
        )
        return False

    def terminate(self) -> None:
        """Attempt to terminate the process described by this info."""
        try:
            log.info(f"Terminating {self.pid}")
            psutil.Process(self.pid).terminate()
        except Exception as e:
            log.info(f"Terminate failed for {self.pid}.")
            log.exception(e, exc_info=True)

    def url(self) -> str:
        return f"{self.binding}:{self.port}"


def get_running_servers() -> t.List[RunningServerInfo]:
    """
    Processes the ~/.ptx/running_servers file to retrieve a list
    of any possibly current running servers.
    """
    if not home_path().exists():
        return []
    try:
        runningServersFile = home_path() / "running_servers"
        if not runningServersFile.is_file():
            return []
        with open(runningServersFile, "r") as f:
            return [RunningServerInfo.fromFileLine(line) for line in f.readlines()]
    except IOError as e:
        log.info("Unable to open running servers file.")
        log.exception(e, exc_info=True)
        return []


def save_running_servers(runningServers: t.List[RunningServerInfo]) -> None:
    """
    Overwrites the ~/.ptx/running_servers file to store
    the new list of running servers.
    """
    # Ensure home path exists
    os.makedirs(home_path(), exist_ok=True)
    try:
        runningServersFile = home_path() / "running_servers"
        with open(runningServersFile, "w") as f:
            # Write each server info to a new line
            f.writelines([f"{info.toFileLine()}\n" for info in runningServers])
    except IOError as e:
        log.info("Unable to write running servers file.")
        log.exception(e, exc_info=True)


def add_server_entry(pathHash: str, pid: int, port: int, binding: str) -> None:
    """Add a new server entry to ~/.ptx/running_servers.

    This function does not attempt to ensure that an active server doesn't already exist.
    """
    PURGE_LIMIT = 10  # If more servers active, try to clean up
    runningServers = get_running_servers()
    newEntry = RunningServerInfo(pathHash=pathHash, pid=pid, port=port, binding=binding)
    runningServers.append(newEntry)
    if len(runningServers) >= PURGE_LIMIT:
        log.info(f"There are {PURGE_LIMIT} or more servers on file. Cleaning up ...")
        runningServers = list(stop_inactive_servers(runningServers))
    save_running_servers(runningServers)
    log.info(f"Added server entry {newEntry.toFileLine()}")


def remove_server_entry(pathHash: str) -> None:
    remainingServers = [
        info for info in get_running_servers() if info.pathHash != pathHash
    ]
    save_running_servers(remainingServers)


def stop_inactive_servers(
    servers: t.List[RunningServerInfo],
) -> t.Iterator[RunningServerInfo]:
    """Stops any inactive servers and yields the active ones."""
    for server in servers:
        if server.isActiveServer():
            yield server
        else:
            server.terminate()


def active_server_for_path_hash(pathHash: str) -> t.Optional[RunningServerInfo]:
    return next(
        (info for info in get_running_servers() if info.pathHash == pathHash),
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
    log.info("setting up ...")
    pathHash = hash_path(base_dir)
    pid = os.getpid()
    port = 8128
    binding = binding_for_access(access)
    log.info("values set...")

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
                log.info("adding server entry")
                add_server_entry(pathHash, pid, port, binding)
                log.info("Starting the server")
                if callback is not None:
                    callback(port)
                httpd.serve_forever()
        except OSError:
            log.warning(f"Port {port} could not be used.")
            port += 1
            log.warning(f"Trying port {port} instead.\n")
        except KeyboardInterrupt:
            log.info("Stopping server.")
            remove_server_entry(pathHash)
            return
