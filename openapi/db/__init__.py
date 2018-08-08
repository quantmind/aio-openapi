import os

from .commands import db
from ..db.dbmodel import CrudDB


def setup_app(app):
    store = os.environ.get('DATASTORE')
    if not store:
        app.logger.warning('DATASTORE not available')
    else:
        app['db'] = CrudDB(store)
    app['cli'].add_command(db)
