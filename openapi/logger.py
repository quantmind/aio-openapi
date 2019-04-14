import logging
import os

import click

try:
    import colorlog
except ImportError:  # pragma: no cover
    colorlog = None


LEVEL = (os.environ.get("LOG_LEVEL") or "info").upper()
LOGGER_NAME = os.environ.get("APP_NAME") or "openapi"
LOG_FORMAT = "%(levelname)s: %(name)s: %(message)s"

logger = logging.getLogger(LOGGER_NAME)


def getLogger(name=None):
    if not name:
        return logger
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


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
