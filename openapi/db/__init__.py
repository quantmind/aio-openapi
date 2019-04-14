import os

from aiohttp.web import Application

from ..db.dbmodel import CrudDB
from .commands import db


def get_db(app: Application, store_url: str = None, command: bool = True) -> CrudDB:
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
    else:
        app["db"] = CrudDB(store_url)
        app.on_shutdown.append(close_db)
        if command:
            app["cli"].add_command(db)
        return app["db"]


async def close_db(app):
    await app["db"].close()
