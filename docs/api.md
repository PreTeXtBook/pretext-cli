# Using PreTeXt as a library

The PreTeXt-CLI includes `Project` and `Target` classes which can be used when this package is imported as a library.

More details are coming soon.

## Logging

This package uses python's logging library and implements a logger with name `"ptxlogger"`.  To get the same messages as the CLI gives (with default level of `INFO`), you can include the following.

```python
import logging
from pretext import logger

log = logging.getLogger("ptxlogger")
logger.add_log_stream_handler()
log.setLevel(logging.INFO)
```

The `logger.add_log_stream_handler()` function simply creates a stream-handler that outputs to stdout.  You could set up `log` however you like using the options provided by the `logging` library.  If you would like to get spit out the logs to a file as the CLI does, you could include the line

```python
logger.add_log_file_handler(path_to_log_directory)
```
