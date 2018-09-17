from copy import copy

import click

from sqlalchemy_utils import database_exists, drop_database, create_database

from .migrations import Migration


def migration(ctx):
    return Migration(ctx.obj['app'])


@click.group()
def db():
    """Perform database migrations."""
    pass


@db.command()
@click.pass_context
def init(ctx):
    """Creates a new migration repository."""
    migration(ctx).init()


@db.command()
@click.option('-m', '--message', help='Revision message', required=True)
@click.option('--branch-label',
              help='Specify a branch label to apply to the new revision')
@click.pass_context
def migrate(ctx, message, branch_label):
    """Autogenerate a new revision file

    alias for 'revision --autogenerate'
    """
    return migration(ctx).revision(
        message,
        autogenerate=True,
        branch_label=branch_label
    )


@db.command()
@click.option('-m', '--message', help='Revision message', required=True)
@click.option('--branch-label',
              help='Specify a branch label to apply to the new revision')
@click.option('--autogenerate', default=False, is_flag=True,
              help=('Populate revision script with candidate migration '
                    'operations, based on comparison of database to model'))
@click.pass_context
def revision(ctx, message, branch_label, autogenerate):
    """Autogenerate a new revision file
    """
    return migration(ctx).revision(
        message,
        autogenerate=autogenerate,
        branch_label=branch_label
    )


@db.command()
@click.option('--revision', default='heads')
@click.option('--drop-tables', default=False, is_flag=True,
              help="Drop tables before applying migrations")
@click.pass_context
def upgrade(ctx, revision, drop_tables):
    """Upgrade to a later version
    """
    if drop_tables:
        _drop_tables(ctx)
    migration(ctx).upgrade(revision)
    click.echo(f"upgraded sucessfuly to {revision}")


@db.command()
@click.option('--revision', default='heads')
@click.option('--drop-tables', default=False, is_flag=True,
              help="Drop tables before applying migrations")
@click.pass_context
def downgrade(ctx, revision, drop_tables):
    """Downgrade to a previous version
    """
    if drop_tables:
        _drop_tables(ctx)
    migration(ctx).downgrade(revision)
    click.echo(f"downgraded successfully to {revision}")


def _drop_tables(ctx):
    ctx.obj['app']['db'].drop_all_schemas()
    click.echo("tables dropped")


@db.command()
@click.option('--revision', default='heads')
@click.pass_context
def show(ctx, revision):
    """Show revision ID and creation date
    """
    return migration(ctx).show(revision)


@db.command()
@click.option('--verbose/--quiet', default=False)
@click.pass_context
def current(ctx, verbose):
    """Show revision ID and creation date
    """
    res = migration(ctx).current(verbose)
    click.echo(res)
    return res


@db.command()
@click.argument('dbname', nargs=1)
@click.option('--force', default=False, is_flag=True,
              help='Force removal of an existing database')
@click.pass_context
def create(ctx, dbname, force):
    """Creates a new database
    """
    engine = ctx.obj['app']['db'].engine
    url = copy(engine.url)
    url.database = dbname
    store = str(url)
    if database_exists(store):
        if force:
            drop_database(store)
        else:
            return click.echo(f'database {dbname} already available')
    create_database(store)
    click.echo(f'database {dbname} created')
