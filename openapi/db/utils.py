from copy import copy

import sqlalchemy as sa

from ..exc import ImproperlyConfigured


def create_tables(app: object) -> None:
    """Create tables defined in app
    """
    engine = app.get('store')
    if not engine:
        raise ImproperlyConfigured('DATASTORE not available')
    app['metadata'].create_all(engine)


def create_database(app: object, database: str) -> object:
    """Create a new database from the existing app store
    Return the new SqlAlchemy engine
    """
    engine = app.get('store')
    if not engine:
        raise ImproperlyConfigured('DATASTORE not available')
    if engine.url.database == database:
        raise ImproperlyConfigured('database %s exists already' % database)
    drop_database(app, database)
    execute(engine, 'create database %s' % database, True)
    url = copy(engine.url)
    url.database = database
    return sa.create_engine(str(url))


def exist_database(app: object, database: str) -> bool:
    """Check if a database exists in the app store
    """
    engine = app.get('store')
    if not engine:
        return False
    text = "SELECT 1 FROM pg_database WHERE datname='%s'" % database
    return bool(execute(engine, text).scalar())


def drop_database(app: object, database: str) -> bool:
    """Drop a database if it exists in the app store
    """
    if exist_database(app, database):
        execute(app.get('store'), 'drop database %s' % database, True)
        return True
    return False


def execute(engine: object, command: str, pre_commit: bool=False) -> object:
    conn = engine.connect()
    try:
        # the connection will still be inside a transaction,
        # so we have to end the open transaction with a commit
        if pre_commit:
            conn.execute("commit")
        return conn.execute(command)
    finally:
        conn.close()
