from ..exc import ImproperlyConfigured


def create_tables(app: object) -> None:
    """Create tables defined in app
    """
    engine = app.get('store')
    if not engine:
        raise ImproperlyConfigured('DATASTORE not available')
    app['metadata'].create_all(engine)
