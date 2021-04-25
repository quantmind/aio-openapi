import logging
import os

import click

try:
    import colorlog
except ImportError:  # pragma: no cover
    colorlog = None


LEVEL = (os.environ.get("LOG_LEVEL") or "info").upper()
LOGGER_NAME = os.environ.get("APP_NAME") or ""
LOG_FORMAT = "%(levelname)s: %(name)s: %(message)s"

logger = logging.getLogger(LOGGER_NAME)


def get_logger(name: str = "") -> logging.Logger:
    return logger.getChild(name) if name else logger


getLogger = get_logger


@click.pass_context
def setup_logging(ctx, verbose, quiet):
    if verbose:
        level = "DEBUG"
    elif quiet:
        level = "ERROR"
    else:
        level = LEVEL
    level = getattr(logging, level) if level != "NONE" else None
    ctx.obj["log_level"] = level
    if level:
        logger.setLevel(level)
        if not logger.hasHandlers():
            fmt = LOG_FORMAT
            if colorlog:
                handler = colorlog.StreamHandler()
                fmt = colorlog.ColoredFormatter(f"%(log_color)s{LOG_FORMAT}")
            else:  # pragma: no cover
                handler = logging.StreamHandler()
                fmt = logging.Formatter(LOG_FORMAT)
            handler.setFormatter(fmt)
            logger.addHandler(handler)
