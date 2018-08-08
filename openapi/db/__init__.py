import os

from .commands import db
from .container import Database


def setup_app(app):
    store = os.environ.get('DATASTORE')
    if not store:
        app.logger.warning('DATASTORE not available')
    else:
        app['db'] = Database(store)
        app['db'].setup(app)
    app['cli'].add_command(db)
