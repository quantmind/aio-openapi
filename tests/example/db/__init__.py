import os

from aiohttp.web import Application

from openapi.db import CrudDB, get_db

from .tables1 import meta
from .tables2 import additional_meta

DEFAULT_DB = "postgresql://postgres:postgres@localhost:5432/openapi"


def setup(app: Application) -> CrudDB:
    return setup_tables(get_db(app))


def setup_tables(db: CrudDB) -> CrudDB:
    additional_meta(meta(db.metadata))
    return db


DB = setup_tables(CrudDB(os.getenv("DATASTORE", DEFAULT_DB)))
