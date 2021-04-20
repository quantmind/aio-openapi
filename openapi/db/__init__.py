import os
from typing import Optional

from aiohttp.web import Application

from .container import Database
from .dbmodel import CrudDB

__all__ = ["compile_query", "Database", "CrudDB", "get_db"]


def get_db(app: Application, store_url: Optional[str] = None) -> Optional[CrudDB]:
    """Create an Open API db handler

    This function
    * add the database to the aiohttp application
    * add the db command to the command line client (if command is True)
    * add the close handler on shutdown

    It returns the database object
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
