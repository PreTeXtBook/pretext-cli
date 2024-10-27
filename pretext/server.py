from dataclasses import dataclass
import logging
import os
import typing as t
import psutil

from pretext.utils import home_path

# Get access to logger
log = logging.getLogger("ptxlogger")


@dataclass
class RunningServerInfo:
    """A simple dataclass to hold the information in the running servers file."""

    pathHash: str
    pid: int
    port: int
    binding: str

    def fromFileLine(line: str):
        (pathHash, pid, port, binding) = line.split()
        return RunningServerInfo(
            pathHash=pathHash, pid=int(pid), port=int(port), binding=binding
        )

    def toFileLine(self) -> str:
        return f"{self.pathHash} {self.pid} {self.port} {self.binding}"

    def isActiveServer(self) -> str:
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

    def terminate(self):
        """Attempt to terminate the process described by this info."""
        try:
            log.info(f"Terminating {self.pid}")
            psutil.Process(self.pid).terminate()
        except Exception as e:
            log.info(f"Terminate failed for {self.pid}.")
            log.exception(e, exc_info=True)

    def url(self):
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


def save_running_servers(runningServers: t.Iterator[RunningServerInfo]) -> None:
    """
    Overwrites the ~/.ptx/running_servers file to store
    the new list of running servers.
    """
    # Ensure home path exists
    os.makedirs(home_path(), exist_ok=True)
    try:
        runningServersFile = home_path() / "running_servers"
        with open(runningServersFile, "w") as f:
            f.writelines([info.toFileLine() for info in runningServers])
    except IOError as e:
        log.info("Unable to write running servers file.")
        log.exception(e, exc_info=True)


def add_server_entry(pathHash: str, pid: id, port: int, binding: str) -> None:
    """Add a new server entry to ~/.ptx/running_servers.

    This function does not attempt to ensure that an active server doesn't already exist.
    """
    PURGE_LIMIT = 10  # If more servers active, try to clean up
    runningServers = get_running_servers()
    newEntry = RunningServerInfo(pathHash=pathHash, pid=pid, port=port, binding=binding)
    runningServers.add(newEntry)
    if len(runningServers) >= PURGE_LIMIT:
        log.info(f"There are {PURGE_LIMIT} or more servers on file. Cleaning up ...")
        runningServers = stop_inactive_servers(runningServers)
    save_running_servers(runningServers)
    log.info(f"Added server entry {newEntry.toFileLine()}")


def stop_inactive_servers(
    servers: t.List[RunningServerInfo],
) -> t.Iterator[RunningServerInfo]:
    """Stops any inactive servers and yields the active ones."""
    for server in servers:
        if server.isActiveServer():
            yield server
        else:
            server.terminate()


def active_server_for_pathHash(pathHash: str) -> t.Optional[RunningServerInfo]:
    return next(
        (info for info in get_running_servers() if info.pathHash == pathHash),
        default=None,
    )
