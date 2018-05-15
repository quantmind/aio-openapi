import os

import sqlalchemy as sa
import asyncpg

from .commands import db


def setup_app(app):
    store = os.environ.get('DATASTORE')
    if not store:
        app.logger.warning('DATASTORE not available')
    else:
        app['store'] = sa.create_engine(store)
    app['cli'].add_command(db)
    app['metadata'] = sa.MetaData()
    app.on_startup.append(init_pg)


async def init_pg(app):
    dsn = str(app['store'].url)
    app.logger.debug('setting up database %s', dsn)
    app['db'] = await asyncpg.create_pool(dsn=dsn)
