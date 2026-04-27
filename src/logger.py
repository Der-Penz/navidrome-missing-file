import logging
import os
from pathlib import Path


class ForceFlushHandler(logging.FileHandler):
    """
    A FileHandler that forces an OS-level sync on every log emission.
    """

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        if self.stream:
            # * Standard Python buffer flush
            self.stream.flush()
            # ! Force the Operating System to write to the physical disk
            os.fsync(self.stream.fileno())


def setup_logger(log_path: Path | None = None) -> None:
    """
    Configures the root logger to use the ForceFlushHandler.

    Parameters
    ----------
    log_path : Path
        The path to the log file.
    """
    if log_path is None:
        log_path = Path("app.log")

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # * Remove existing handlers if any
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    custom_handler = ForceFlushHandler(log_path, mode="a")
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    custom_handler.setFormatter(formatter)

    logger.addHandler(custom_handler)
