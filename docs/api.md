# Using pretext-cli as a Python library

The `pretext-cli` package can be used directly from Python, without spawning
CLI subprocesses.

The two main entry points are:

- `Project.parse(...)`: load an existing `project.ptx` manifest.
- `Project(...)` + `new_target(...)`: build projects programmatically when no
  manifest exists.

## Quick start

```python
from pathlib import Path
from pretext import project as pr

# Case 1: You already have project.ptx
project = pr.Project.parse(Path("."))
project.get_target("web").build()

# Case 2: No project.ptx (for example, core/examples/epub)
project = pr.Project(ptx_version="2", source=Path(""), publication=Path(""))
target = project.new_target(
    "ebook",
    "epub",
    source=Path("epub-sampler.xml"),
    publication=Path("publication.xml"),
)
target.build()
```

## Why set `source` and `publication` to `Path("")`?

`Project` prepends its own base paths to each target's `source` and
`publication` paths.

- Default `Project.source` is `source/`.
- Default `Project.publication` is `publication/`.

When your files live directly in the project root (as in the core EPUB
example), setting both to `Path("")` makes target paths resolve from that root.

## Logging

To mirror CLI-style log output in library usage:

```python
import logging
from pretext import logger

log = logging.getLogger("ptxlogger")
logger.add_log_stream_handler()
log.setLevel(logging.INFO)
```

To also log to files:

```python
logger.add_log_file_handler(path_to_log_directory)
```

## Version reporting

If you want the running CLI version in your app logs, either:

- call `utils.report_version()` for the built-in message, or
- import `VERSION` and log it yourself.
