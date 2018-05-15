import click

from .migrations import Migration


def migration(ctx):
    return Migration(ctx.parent.parent.app)


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
@click.pass_context
def upgrade(ctx, revision):
    """Upgrade to a later version
    """
    return migration(ctx).upgrade(revision)
