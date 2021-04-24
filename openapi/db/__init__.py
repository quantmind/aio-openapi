import os
from typing import Optional

from aiohttp.web import Application

from .container import Database
from .dbmodel import CrudDB

__all__ = ["compile_query", "Database", "CrudDB", "get_db"]


def get_db(app: Application, store_url: Optional[str] = None) -> Optional[CrudDB]:
    """Create an Open API db handler and set it for use in an aiohttp application

    :param app: aiohttp Application
    :param store_url: datastore connection string, if not provided the env
        variable `DATASTORE` is used instead. If the env variable is not available
        either the method logs a warning and return `None`

    This function 1) adds the database to the aiohttp application at key "db",
    2) add the db command to the command line client (if command is True)
    and 3) add the close handler on application shutdown
    """
    store_url = store_url or os.environ.get("DATASTORE")
    if not store_url:  # pragma: no cover
        app.logger.warning("DATASTORE url not available")
        return None
    else:
        app["db"] = CrudDB(store_url)
        app.on_shutdown.append(close_db)
        return app["db"]


async def close_db(app: Application) -> None:
    await app["db"].close()
